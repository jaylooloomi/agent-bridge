# Agent Bridge (`agent-bridge`)

**Local Agent Mesh Daemon & Unified MCP Hub** — 讓 **Codex**、**Claude** 與 **Antigravity (AGY)** 透過單一工具互相發現、雙向調用，並讓 Codex 與 Claude 能直接呼叫 Antigravity 產生高畫質圖片（`.jpg`/`.png`）與動態短片（`.mp4`）。

---

## ✨ 核心特色（方案三：常駐守護進程 + A2A 即時通訊匯流排）

1. **一鍵安裝，三方互連**：
   執行 `agent-bridge-install`，自動將 `agent-bridge-mcp` 掛載至：
   - **Codex** (`~/.codex/config.toml`)
   - **Claude Code** (`~/.claude.json`)
   - **Antigravity** (`~/.gemini/config/mcp_config.json`)
2. **免額外 API Key 的 Antigravity 原生多媒體橋接**：
   - 優先串接本機已登入的 Antigravity Daemon (`~/.gemini/antigravity/bin/agentapi.bat`) 喚起內建 `image-generator` 產生 AI 圖片，並結合 FFmpeg (`libx264`) 進行平滑運鏡與關鍵影格合成產出 720p `.mp4` 短片。
   - 同時支援 `google-antigravity` Python SDK 與本地離線引擎備援，確保 100% 穩定交付檔案路徑。
3. **自癒式背景常駐 Daemon (Auto-Spawn)**：
   - 當任一 Agent 呼叫 MCP 工具時，若本地 `Agent Mesh Daemon` (`127.0.0.1:8765`) 尚未啟動，`agent-bridge-mcp` 會自動在背景拉起常駐服務。
4. **防死循環防火牆 (Hop Firewall)**：
   - 內建 `hop_count`、`max_hops`（預設最多 3 跳）與 `call_chain` 追蹤，防止 Agent A ⇄ B 產生無限遞迴調用。

---

## 🚀 快速開始

### 1. 安裝套件與環境

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"
```

### 2. 一鍵註冊至 Codex、Claude 與 Antigravity

```powershell
.\.venv\Scripts\agent-bridge-install.exe
```

### 3. 在 Codex 或 Claude 中使用

你可以直接在 **Codex** 或 **Claude** 對話中輸入：
- *「請透過 agent-bridge 幫我呼叫 Antigravity 產生一張賽博龐克太空貓的圖片，存在 `d:/git/agent-bridge/outputs`」*
- *「請呼叫 `generate_video` 產生一段 5 秒的太空貓飛行短片 (.mp4)」*
- *「查詢目前有哪些註冊的 Agent 支援 `image_generation` 或 `code_review`」*

---

## 🛠️ 架構與通訊協定文件

詳細的系統架構圖、JSON Schema 與 MCP 工具列表請參閱 [docs/architecture.md](docs/architecture.md)。
