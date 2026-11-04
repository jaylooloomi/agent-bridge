"""Codex Worker: Invokes local OpenAI Codex CLI (`codex exec`) in headless mode."""

from __future__ import annotations

import asyncio
from pathlib import Path

from agent_bridge.protocol import AgentTaskRequest, TaskResultPayload
from agent_bridge.registry import find_codex_cli


class CodexWorker:
    """Executes tasks assigned to OpenAI Codex via `codex exec`."""

    async def execute(self, request: AgentTaskRequest) -> TaskResultPayload:
        codex_bin = find_codex_cli()
        if not codex_bin:
            raise RuntimeError("OpenAI Codex CLI (`codex`) was not found on this machine.")

        workspace = request.context.get("workspace") or str(Path.cwd())
        timeout_sec = float(request.parameters.get("timeout_sec", 120.0))

        # Build headless codex exec command
        cmd = [
            codex_bin,
            "exec",
            "--skip-git-repo-check",
            "-C",
            str(workspace),
            request.prompt,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
        stdout_text = stdout_bytes.decode("utf-8", errors="replace").strip()
        stderr_text = stderr_bytes.decode("utf-8", errors="replace").strip()

        if proc.returncode != 0 and not stdout_text:
            raise RuntimeError(f"Codex CLI exited with code {proc.returncode}: {stderr_text}")

        combined = stdout_text or stderr_text
        summary = combined[:400] + ("..." if len(combined) > 400 else "")
        return TaskResultPayload(
            summary=summary or "Codex task completed.",
            artifacts=[],
            raw_output=combined,
            metadata={"backend": "codex_cli", "return_code": proc.returncode},
        )
