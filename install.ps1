$ErrorActionPreference = "Stop"
$Dest = if ($env:AGENT_BRIDGE_HOME) { $env:AGENT_BRIDGE_HOME } else { Join-Path $HOME ".agent-bridge" }
Write-Host "==> Installing agent-bridge into $Dest ..." -ForegroundColor Cyan

if (Test-Path (Join-Path $Dest ".git")) {
    git -C $Dest pull --ff-only
} else {
    git clone https://github.com/jaylooloomi/agent-bridge.git $Dest
}

python -m venv (Join-Path $Dest ".venv")
& (Join-Path $Dest ".venv\Scripts\pip.exe") install -e $Dest
& (Join-Path $Dest ".venv\Scripts\agent-bridge-install.exe")

Write-Host "==> Done! Restart your Claude / Codex / Antigravity session to use agent-bridge." -ForegroundColor Green
