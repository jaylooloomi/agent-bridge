---
name: agent-bridge
description: >-
  Connects Claude Code, OpenAI Codex, and Google Antigravity into a bidirectional Local Agent Mesh (:8765).
  Activate this skill whenever the user asks to generate images, icons, illustrations, or MP4 videos
  (delegated to Antigravity), or when the user asks to discover or call another agent (antigravity, codex, claude),
  or to install/configure agent-bridge.
---

# Agent Bridge Skill (`agent-bridge`)

You have access to the **Agent Bridge** (`agent-bridge-mcp` + Local Agent Mesh Daemon at `http://127.0.0.1:8765`), which links **Claude Code**, **OpenAI Codex**, and **Google Antigravity (AGY)**.

## 1. When MCP Tools Are Mounted (Preferred)

If the `agent-bridge` MCP server is active in your session, call its tools directly:

- **`generate_image(prompt, output_dir, filename_prefix, aspect_ratio)`**:
  Use whenever you need to generate an image, icon, banner, or UI asset (especially in Claude Code, which cannot generate images natively). Delegates to Antigravity's `image-generator` and saves the file locally.
- **`generate_video(prompt, output_dir, filename_prefix, duration_sec, aspect_ratio)`**:
  Use whenever you need an `.mp4` animation or background video. Antigravity generates a high-resolution keyframe and synthesizes a smooth 720p `libx264` MP4 video.
- **`discover_agents(capability)`**:
  Query live online agents and filter by capability (`image_generation`, `video_generation`, `code_review`, `code_execution`).
- **`call_agent(target_agent, prompt, task_type, workspace, hop_count)`**:
  Invoke `antigravity`, `codex`, or `claude` bidirectionally. Built-in Hop Firewall blocks loops (`max_hops = 3`).
- **`get_task_result(task_id, wait, timeout_sec)`**:
  Wait for or poll asynchronous tasks.

## 2. Self-Bootstrap / Auto-Install Procedure

If the user gives you the repository URL `https://github.com/jaylooloomi/agent-bridge` and says **"Help me install this"** (or if the `agent-bridge` MCP tools are not yet mounted in your environment), run the following commands automatically:

### Windows (PowerShell)
```powershell
git clone https://github.com/jaylooloomi/agent-bridge.git "$HOME\.agent-bridge" 2>$null; if (-not $?) { git -C "$HOME\.agent-bridge" pull }
python -m venv "$HOME\.agent-bridge\.venv"
& "$HOME\.agent-bridge\.venv\Scripts\pip.exe" install -e "$HOME\.agent-bridge"
& "$HOME\.agent-bridge\.venv\Scripts\agent-bridge-install.exe"
```

### macOS / Linux / WSL / Git Bash
```bash
git clone https://github.com/jaylooloomi/agent-bridge.git ~/.agent-bridge || git -C ~/.agent-bridge pull
python3 -m venv ~/.agent-bridge/.venv
~/.agent-bridge/.venv/bin/pip install -e ~/.agent-bridge
~/.agent-bridge/.venv/bin/agent-bridge-install
```

After running `agent-bridge-install`, report to the user that `agent-bridge` has been registered into:
- **Claude Code** (`~/.claude.json`)
- **OpenAI Codex** (`~/.codex/config.toml`)
- **Google Antigravity** (`~/.gemini/config/mcp_config.json`)
