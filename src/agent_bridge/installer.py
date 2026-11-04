"""Installer utility to register `agent-bridge-mcp` across Codex, Claude, and Antigravity."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys


def get_python_executable() -> str:
    return str(Path(sys.executable).resolve())


def install_antigravity_mcp(python_exe: str, dry_run: bool = False) -> str:
    """Register agent-bridge in ~/.gemini/config/mcp_config.json."""
    home = Path(os.environ.get("USERPROFILE", str(Path.home())))
    config_path = home / ".gemini" / "config" / "mcp_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    data: dict = {}
    if config_path.exists():
        raw = config_path.read_text(encoding="utf-8", errors="replace").strip()
        if raw:
            try:
                data = json.loads(raw)
            except Exception:
                data = {}

    if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
        data["mcpServers"] = {}

    data["mcpServers"]["agent-bridge"] = {
        "command": python_exe,
        "args": ["-m", "agent_bridge.mcp_server"],
        "env": {
            "AGENT_BRIDGE_CALLER": "antigravity",
            "AGENT_BRIDGE_DAEMON_URL": "http://127.0.0.1:8765",
        },
    }

    if not dry_run:
        config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(config_path)


def install_codex_mcp(python_exe: str, dry_run: bool = False) -> str:
    """Register agent-bridge in ~/.codex/config.toml."""
    home = Path(os.environ.get("USERPROFILE", str(Path.home())))
    config_path = home / ".codex" / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    content = ""
    if config_path.exists():
        content = config_path.read_text(encoding="utf-8", errors="replace")

    # Remove existing [mcp_servers.agent_bridge] and [mcp_servers.agent_bridge.env] blocks if present
    content = re.sub(
        r"\n*\[mcp_servers\.agent_bridge(?:\.env)?\][^\[]*",
        "",
        content,
        flags=re.DOTALL,
    ).rstrip()

    escaped_py = python_exe.replace("\\", "\\\\")
    block = (
        f"\n\n[mcp_servers.agent_bridge]\n"
        f'command = "{escaped_py}"\n'
        f'args = ["-m", "agent_bridge.mcp_server"]\n'
        f"startup_timeout_sec = 60\n\n"
        f"[mcp_servers.agent_bridge.env]\n"
        f'AGENT_BRIDGE_CALLER = "codex"\n'
        f'AGENT_BRIDGE_DAEMON_URL = "http://127.0.0.1:8765"\n'
    )
    new_content = content + block
    if not dry_run:
        config_path.write_text(new_content, encoding="utf-8")
    return str(config_path)


def install_claude_mcp(python_exe: str, dry_run: bool = False) -> str:
    """Register agent-bridge in ~/.claude.json."""
    home = Path(os.environ.get("USERPROFILE", str(Path.home())))
    config_path = home / ".claude.json"

    data: dict = {}
    if config_path.exists():
        raw = config_path.read_text(encoding="utf-8", errors="replace").strip()
        if raw:
            try:
                data = json.loads(raw)
            except Exception:
                data = {}

    if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
        data["mcpServers"] = {}

    data["mcpServers"]["agent-bridge"] = {
        "type": "stdio",
        "command": python_exe,
        "args": ["-m", "agent_bridge.mcp_server"],
        "env": {
            "AGENT_BRIDGE_CALLER": "claude",
            "AGENT_BRIDGE_DAEMON_URL": "http://127.0.0.1:8765",
        },
    }

    if not dry_run:
        config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(config_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Register agent-bridge MCP server across Codex, Claude, and Antigravity.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying files.")
    args = parser.parse_args()

    py_exe = get_python_executable()
    p_agy = install_antigravity_mcp(py_exe, dry_run=args.dry_run)
    p_codex = install_codex_mcp(py_exe, dry_run=args.dry_run)
    p_claude = install_claude_mcp(py_exe, dry_run=args.dry_run)

    print("Successfully configured agent-bridge MCP server for all 3 agents:")
    print(f"  - Antigravity : {p_agy}")
    print(f"  - Codex       : {p_codex}")
    print(f"  - Claude      : {p_claude}")


if __name__ == "__main__":
    main()
