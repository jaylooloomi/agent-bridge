"""Thin MCP Client/Server Adapter (`agent-bridge-mcp`) for Codex, Claude, and Antigravity."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from typing import Any
import httpx

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer  # type: ignore

from agent_bridge.protocol import AgentId, TaskType

DAEMON_URL = os.environ.get("AGENT_BRIDGE_DAEMON_URL", "http://127.0.0.1:8765").rstrip("/")
CALLER_IDENTITY = os.environ.get("AGENT_BRIDGE_CALLER", "mcp_client")

mcp = MCPServer(
    name="agent-bridge",
    instructions=(
        "Agent Bridge connects Codex, Claude, and Antigravity into a bidirectional Agent Mesh. "
        "Use `generate_image` or `generate_video` whenever the user asks to generate images, icons, illustrations, "
        "animations, or videos (delegated automatically to Antigravity). "
        "Use `discover_agents` and `call_agent` to collaborate with other agents (antigravity, codex, claude)."
    ),
)


async def ensure_daemon_running() -> str:
    """Verify the Local Agent Mesh Daemon is reachable; if not, spawn it in the background automatically."""
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            resp = await client.get(f"{DAEMON_URL}/health")
            if resp.status_code == 200:
                return DAEMON_URL
        except Exception:
            pass

    # Auto-start Daemon in background detached process
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW

    subprocess.Popen(
        [sys.executable, "-m", "agent_bridge.daemon"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
        close_fds=True,
    )

    # Wait up to 8 seconds for daemon to come online
    async with httpx.AsyncClient(timeout=2.0) as client:
        for _ in range(16):
            await asyncio.sleep(0.5)
            try:
                resp = await client.get(f"{DAEMON_URL}/health")
                if resp.status_code == 200:
                    return DAEMON_URL
            except Exception:
                continue

    raise RuntimeError(f"Failed to connect to or auto-start Agent Bridge Daemon at {DAEMON_URL}")


@mcp.tool()
async def discover_agents(capability: str = "") -> str:
    """Discover online agents in the mesh and their registered capabilities (e.g. 'image_generation', 'video_generation', 'code_review', 'code_execution')."""
    base_url = await ensure_daemon_running()
    params = {"capability": capability} if capability else {}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{base_url}/agents", params=params)
        resp.raise_for_status()
        return json.dumps(resp.json(), indent=2, ensure_ascii=False)


@mcp.tool()
async def generate_image(
    prompt: str,
    output_dir: str = "",
    filename_prefix: str = "agy_image",
    aspect_ratio: str = "1:1",
    caller_agent: str = "",
) -> str:
    """Generate an image or illustration by delegating to Antigravity's image generation engine and return the saved file path."""
    base_url = await ensure_daemon_running()
    payload: dict[str, Any] = {
        "caller_agent": caller_agent or CALLER_IDENTITY,
        "target_agent": AgentId.ANTIGRAVITY.value,
        "task_type": TaskType.IMAGE_GENERATION.value,
        "prompt": prompt,
        "output_dir": output_dir or None,
        "parameters": {
            "filename_prefix": filename_prefix,
            "aspect_ratio": aspect_ratio,
        },
        "async_mode": False,
    }
    async with httpx.AsyncClient(timeout=150.0) as client:
        resp = await client.post(f"{base_url}/tasks", json=payload)
        resp.raise_for_status()
        return json.dumps(resp.json(), indent=2, ensure_ascii=False)


@mcp.tool()
async def generate_video(
    prompt: str,
    output_dir: str = "",
    filename_prefix: str = "agy_video",
    duration_sec: float = 5.0,
    aspect_ratio: str = "16:9",
    async_mode: bool = False,
    caller_agent: str = "",
) -> str:
    """Generate an MP4 video animation by delegating to Antigravity's media engine and return the saved video and keyframe paths."""
    base_url = await ensure_daemon_running()
    payload: dict[str, Any] = {
        "caller_agent": caller_agent or CALLER_IDENTITY,
        "target_agent": AgentId.ANTIGRAVITY.value,
        "task_type": TaskType.VIDEO_GENERATION.value,
        "prompt": prompt,
        "output_dir": output_dir or None,
        "parameters": {
            "filename_prefix": filename_prefix,
            "duration_sec": duration_sec,
            "aspect_ratio": aspect_ratio,
        },
        "async_mode": async_mode,
    }
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(f"{base_url}/tasks", json=payload)
        resp.raise_for_status()
        return json.dumps(resp.json(), indent=2, ensure_ascii=False)


@mcp.tool()
async def call_agent(
    target_agent: str,
    prompt: str,
    task_type: str = "general_chat",
    output_dir: str = "",
    workspace: str = "",
    hop_count: int = 0,
    async_mode: bool = False,
    caller_agent: str = "",
) -> str:
    """Call another agent ('antigravity', 'codex', or 'claude') to perform a task. Includes hop_count loop protection."""
    base_url = await ensure_daemon_running()
    payload: dict[str, Any] = {
        "caller_agent": caller_agent or CALLER_IDENTITY,
        "target_agent": target_agent,
        "task_type": task_type,
        "prompt": prompt,
        "output_dir": output_dir or None,
        "context": {"workspace": workspace} if workspace else {},
        "hop_count": hop_count,
        "async_mode": async_mode,
    }
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(f"{base_url}/tasks", json=payload)
        resp.raise_for_status()
        return json.dumps(resp.json(), indent=2, ensure_ascii=False)


@mcp.tool()
async def get_task_result(task_id: str, wait: bool = True, timeout_sec: float = 90.0) -> str:
    """Query or wait for the completion of an asynchronous task by task_id."""
    base_url = await ensure_daemon_running()
    async with httpx.AsyncClient(timeout=timeout_sec + 15.0) as client:
        resp = await client.get(
            f"{base_url}/tasks/{task_id}",
            params={"wait": wait, "timeout_sec": timeout_sec},
        )
        resp.raise_for_status()
        return json.dumps(resp.json(), indent=2, ensure_ascii=False)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
