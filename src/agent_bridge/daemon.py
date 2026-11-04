"""Local Agent Mesh Daemon (FastAPI server): Registry, Task Queue, Firewall, and Worker Router."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import os
import uuid
from fastapi import FastAPI, HTTPException, Query
import uvicorn

from agent_bridge.protocol import (
    AgentDescriptor,
    AgentId,
    AgentTaskRequest,
    AgentTaskResponse,
    TaskStatus,
)
from agent_bridge.registry import AgentRegistry
from agent_bridge.workers.antigravity_worker import AntigravityWorker
from agent_bridge.workers.claude_worker import ClaudeWorker
from agent_bridge.workers.codex_worker import CodexWorker


class AgentMeshHub:
    """Core orchestration engine managing Registry, Firewall, and Async Task Queue."""

    def __init__(self) -> None:
        self.registry = AgentRegistry()
        self.tasks: dict[str, AgentTaskResponse] = {}
        self.task_events: dict[str, asyncio.Event] = {}
        self.workers = {
            AgentId.ANTIGRAVITY.value: AntigravityWorker(),
            AgentId.CODEX.value: CodexWorker(),
            AgentId.CLAUDE.value: ClaudeWorker(),
        }

    def validate_firewall(self, req: AgentTaskRequest) -> None:
        """Enforce hop count limit and prevent cyclic A2A deadlocks."""
        if req.hop_count >= req.max_hops:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Firewall rejected task: hop_count ({req.hop_count}) reached max_hops ({req.max_hops}). "
                    f"Call chain: {req.call_chain}"
                ),
            )
        target = req.target_agent.lower().strip()
        if target not in self.workers:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown target_agent '{req.target_agent}'. Available: {list(self.workers.keys())}",
            )

    async def submit_task(self, req: AgentTaskRequest) -> AgentTaskResponse:
        self.validate_firewall(req)

        task_id = f"task_{uuid.uuid4().hex[:10]}"
        updated_chain = list(req.call_chain)
        if req.caller_agent and (not updated_chain or updated_chain[-1] != req.caller_agent):
            updated_chain.append(req.caller_agent)
        updated_chain.append(req.target_agent.lower().strip())

        task_resp = AgentTaskResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            caller_agent=req.caller_agent,
            target_agent=req.target_agent.lower().strip(),
            task_type=req.task_type,
            hop_count=req.hop_count + 1,
            call_chain=updated_chain,
        )
        event = asyncio.Event()
        self.tasks[task_id] = task_resp
        self.task_events[task_id] = event

        if req.async_mode:
            asyncio.create_task(self._run_worker_task(task_id, req))
            return self.tasks[task_id]

        await self._run_worker_task(task_id, req)
        return self.tasks[task_id]

    async def _run_worker_task(self, task_id: str, req: AgentTaskRequest) -> None:
        record = self.tasks[task_id]
        record.status = TaskStatus.RUNNING
        worker = self.workers[record.target_agent]
        try:
            result = await worker.execute(req)
            record.result = result
            record.status = TaskStatus.COMPLETED
        except Exception as exc:
            record.error = str(exc)
            record.status = TaskStatus.FAILED
        finally:
            record.completed_at = datetime.now(timezone.utc).isoformat()
            if task_id in self.task_events:
                self.task_events[task_id].set()

    async def wait_for_task(self, task_id: str, timeout_sec: float = 120.0) -> AgentTaskResponse:
        if task_id not in self.tasks:
            raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
        event = self.task_events.get(task_id)
        if event and not event.is_set():
            try:
                await asyncio.wait_for(event.wait(), timeout=timeout_sec)
            except asyncio.TimeoutError:
                pass
        return self.tasks[task_id]


hub = AgentMeshHub()
app = FastAPI(
    title="Agent Bridge — Local Agent Mesh Daemon",
    version="0.1.0",
    description="Bidirectional A2A Message Bus & Media Generation Bridge for Codex, Claude, and Antigravity.",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "agent-bridge-daemon", "version": "0.1.0"}


@app.get("/agents", response_model=list[AgentDescriptor])
async def list_agents(capability: str | None = Query(default=None)) -> list[AgentDescriptor]:
    return hub.registry.discover(capability)


@app.post("/agents/register", response_model=AgentDescriptor)
async def register_agent(descriptor: AgentDescriptor) -> AgentDescriptor:
    return hub.registry.register_agent(descriptor)


@app.post("/tasks", response_model=AgentTaskResponse)
async def create_task(request: AgentTaskRequest) -> AgentTaskResponse:
    return await hub.submit_task(request)


@app.get("/tasks", response_model=list[AgentTaskResponse])
async def list_tasks() -> list[AgentTaskResponse]:
    return list(hub.tasks.values())


@app.get("/tasks/{task_id}", response_model=AgentTaskResponse)
async def get_task(
    task_id: str,
    wait: bool = Query(default=False),
    timeout_sec: float = Query(default=60.0),
) -> AgentTaskResponse:
    if wait:
        return await hub.wait_for_task(task_id, timeout_sec=timeout_sec)
    if task_id not in hub.tasks:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    return hub.tasks[task_id]


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the Agent Bridge Local Mesh Daemon.")
    parser.add_argument("--host", default=os.environ.get("AGENT_BRIDGE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("AGENT_BRIDGE_PORT", "8765")))
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
