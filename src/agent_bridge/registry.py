"""Agent capability registry and auto-detection for Antigravity, Codex, and Claude."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from agent_bridge.protocol import AgentDescriptor, AgentId, TaskType


def find_agentapi_bat() -> str | None:
    """Locate Antigravity's native agentapi.bat or language_server.exe."""
    env_override = os.environ.get("AGY_AGENTAPI_PATH")
    if env_override and Path(env_override).exists():
        return str(Path(env_override).resolve())

    home = Path.home()
    candidates = [
        home / ".gemini" / "antigravity" / "bin" / "agentapi.bat",
        Path(os.environ.get("USERPROFILE", str(home))) / ".gemini" / "antigravity" / "bin" / "agentapi.bat",
    ]
    for c in candidates:
        if c.exists():
            return str(c.resolve())

    which_res = shutil.which("agentapi") or shutil.which("agentapi.bat")
    if which_res:
        return which_res
    return None


def find_codex_cli() -> str | None:
    """Locate OpenAI Codex CLI executable."""
    env_override = os.environ.get("CODEX_CLI_PATH")
    if env_override and Path(env_override).exists():
        return str(Path(env_override).resolve())

    which_res = shutil.which("codex.cmd") or shutil.which("codex")
    if which_res:
        return which_res

    appdata = os.environ.get("APPDATA", "")
    if appdata:
        cand = Path(appdata) / "npm" / "codex.cmd"
        if cand.exists():
            return str(cand)
    return None


def find_claude_cli() -> str | None:
    """Locate Anthropic Claude Code CLI executable."""
    env_override = os.environ.get("CLAUDE_CLI_PATH")
    if env_override and Path(env_override).exists():
        return str(Path(env_override).resolve())

    which_res = shutil.which("claude.exe") or shutil.which("claude")
    if which_res:
        return which_res

    home = Path.home()
    cand = home / ".local" / "bin" / "claude.exe"
    if cand.exists():
        return str(cand)
    return None


class AgentRegistry:
    """Maintains the live registry of agents and their capabilities in the mesh."""

    def __init__(self) -> None:
        self._custom_agents: dict[str, AgentDescriptor] = {}

    def get_all_agents(self) -> list[AgentDescriptor]:
        agy_bin = find_agentapi_bat()
        agy_sdk_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
        agy_online = bool(agy_bin or agy_sdk_key)
        agy_mode = "native_agentapi" if agy_bin else ("sdk_genai" if agy_sdk_key else "local_fallback")

        codex_bin = find_codex_cli()
        claude_bin = find_claude_cli()

        builtin = [
            AgentDescriptor(
                agent_id=AgentId.ANTIGRAVITY.value,
                display_name="Google Antigravity (AGY)",
                status="online" if agy_online else "degraded",
                backend_mode=agy_mode,
                capabilities=[
                    TaskType.IMAGE_GENERATION.value,
                    TaskType.VIDEO_GENERATION.value,
                    TaskType.GENERAL_CHAT.value,
                    TaskType.CODE_REVIEW.value,
                ],
                description=(
                    "Specializes in multimedia generation (image_generation via built-in image-generator / Imagen, "
                    "and video_generation via keyframe synthesis & Veo/FFmpeg encoding), ultra-large context analysis, "
                    "and browser automation."
                ),
            ),
            AgentDescriptor(
                agent_id=AgentId.CODEX.value,
                display_name="OpenAI Codex CLI",
                status="online" if codex_bin else "offline",
                backend_mode="codex_cli" if codex_bin else "unavailable",
                capabilities=[
                    TaskType.CODE_EXECUTION.value,
                    TaskType.CODE_REVIEW.value,
                    TaskType.GENERAL_CHAT.value,
                ],
                description=(
                    "Specializes in rapid algorithm implementation, sandboxed test execution, "
                    "CLI batch refactoring, and debugging via `codex exec`."
                ),
            ),
            AgentDescriptor(
                agent_id=AgentId.CLAUDE.value,
                display_name="Anthropic Claude Code",
                status="online" if claude_bin else "offline",
                backend_mode="claude_cli" if claude_bin else "unavailable",
                capabilities=[
                    TaskType.CODE_REVIEW.value,
                    TaskType.CODE_EXECUTION.value,
                    TaskType.GENERAL_CHAT.value,
                ],
                description=(
                    "Specializes in system architecture design, long-form reasoning, frontend aesthetics, "
                    "and deep security/code review via `claude -p`."
                ),
            ),
        ]

        merged = {a.agent_id: a for a in builtin}
        merged.update(self._custom_agents)
        return list(merged.values())

    def discover(self, capability: str | None = None) -> list[AgentDescriptor]:
        agents = self.get_all_agents()
        if not capability:
            return agents
        cap_lower = capability.strip().lower()
        return [
            a
            for a in agents
            if any(cap_lower in c.lower() for c in a.capabilities) or cap_lower in a.description.lower()
        ]

    def register_agent(self, descriptor: AgentDescriptor) -> AgentDescriptor:
        self._custom_agents[descriptor.agent_id] = descriptor
        return descriptor
