"""Claude Worker: Invokes local Anthropic Claude Code CLI (`claude -p`) in headless mode."""

from __future__ import annotations

import asyncio
from pathlib import Path

from agent_bridge.protocol import AgentTaskRequest, TaskResultPayload
from agent_bridge.registry import find_claude_cli


class ClaudeWorker:
    """Executes tasks assigned to Anthropic Claude via `claude -p`."""

    async def execute(self, request: AgentTaskRequest) -> TaskResultPayload:
        claude_bin = find_claude_cli()
        if not claude_bin:
            raise RuntimeError("Claude Code CLI (`claude`) was not found on this machine.")

        workspace = request.context.get("workspace") or str(Path.cwd())
        timeout_sec = float(request.parameters.get("timeout_sec", 120.0))

        cmd = [
            claude_bin,
            "-p",
            request.prompt,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(workspace),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
        stdout_text = stdout_bytes.decode("utf-8", errors="replace").strip()
        stderr_text = stderr_bytes.decode("utf-8", errors="replace").strip()

        if proc.returncode != 0 and not stdout_text:
            raise RuntimeError(f"Claude CLI exited with code {proc.returncode}: {stderr_text}")

        combined = stdout_text or stderr_text
        summary = combined[:400] + ("..." if len(combined) > 400 else "")
        return TaskResultPayload(
            summary=summary or "Claude task completed.",
            artifacts=[],
            raw_output=combined,
            metadata={"backend": "claude_cli", "return_code": proc.returncode},
        )
