"""Comprehensive unit and integration test suite for Agent Bridge (Daemon, Registry, Firewall, Media Generation, and MCP)."""

from __future__ import annotations

from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from agent_bridge.daemon import app, hub
from agent_bridge.protocol import AgentTaskRequest, TaskStatus, TaskType


client = TestClient(app)


def test_health_and_registry_discovery():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # Discover all agents
    agents_resp = client.get("/agents")
    assert agents_resp.status_code == 200
    agents = agents_resp.json()
    agent_ids = {a["agent_id"] for a in agents}
    assert {"antigravity", "codex", "claude"}.issubset(agent_ids)

    # Filter by image_generation capability
    img_agents = client.get("/agents", params={"capability": "image_generation"}).json()
    assert len(img_agents) >= 1
    assert img_agents[0]["agent_id"] == "antigravity"

    # Filter by video_generation capability
    vid_agents = client.get("/agents", params={"capability": "video_generation"}).json()
    assert len(vid_agents) >= 1
    assert vid_agents[0]["agent_id"] == "antigravity"


def test_firewall_hop_limit_enforcement():
    payload = {
        "caller_agent": "codex",
        "target_agent": "antigravity",
        "task_type": "general_chat",
        "prompt": "Loop test",
        "hop_count": 3,
        "max_hops": 3,
        "call_chain": ["codex", "claude", "antigravity"],
    }
    resp = client.post("/tasks", json=payload)
    assert resp.status_code == 400
    assert "Firewall rejected task" in resp.json()["detail"]


def test_codex_calls_antigravity_procedural_image_and_video(tmp_path: Path):
    # 1. Test fast image generation pipeline
    img_payload = {
        "caller_agent": "codex",
        "target_agent": "antigravity",
        "task_type": TaskType.IMAGE_GENERATION.value,
        "prompt": "A neon futuristic robot cat badge",
        "output_dir": str(tmp_path),
        "parameters": {
            "filename_prefix": "unit_test_img",
            "force_procedural": True,
        },
    }
    resp = client.post("/tasks", json=img_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == TaskStatus.COMPLETED.value
    assert data["hop_count"] == 1
    assert data["call_chain"] == ["codex", "antigravity"]
    artifacts = data["result"]["artifacts"]
    assert len(artifacts) == 1
    img_file = Path(artifacts[0]["path"])
    assert img_file.exists()
    assert img_file.stat().st_size > 1000

    # 2. Test video generation pipeline (synthesizes MP4 video + keyframe)
    vid_payload = {
        "caller_agent": "codex",
        "target_agent": "antigravity",
        "task_type": TaskType.VIDEO_GENERATION.value,
        "prompt": "A cyberpunk space cat flying through a neon nebula",
        "output_dir": str(tmp_path),
        "parameters": {
            "filename_prefix": "unit_test_vid",
            "duration_sec": 2.0,
            "force_procedural": True,
        },
    }
    v_resp = client.post("/tasks", json=vid_payload)
    assert v_resp.status_code == 200
    v_data = v_resp.json()
    assert v_data["status"] == TaskStatus.COMPLETED.value
    v_artifacts = v_data["result"]["artifacts"]
    assert len(v_artifacts) == 2
    video_file = Path(v_artifacts[0]["path"])
    assert video_file.suffix == ".mp4"
    assert video_file.exists()
    assert video_file.stat().st_size > 5000


@pytest.mark.asyncio
async def test_real_native_antigravity_image_and_video(tmp_path: Path):
    """End-to-end test invoking the real Antigravity native `agentapi.bat` image-generator + MP4 video synthesizer."""
    req = AgentTaskRequest(
        caller_agent="codex",
        target_agent="antigravity",
        task_type=TaskType.VIDEO_GENERATION.value,
        prompt="Cute minimalist futuristic space cat astronaut emblem, vibrant neon blue and gold, clean game art",
        output_dir=str(tmp_path),
        parameters={
            "filename_prefix": "e2e_codex_to_agy",
            "duration_sec": 3.0,
            "aspect_ratio": "16:9",
        },
    )
    resp = await hub.submit_task(req)
    assert resp.status == TaskStatus.COMPLETED
    assert resp.result is not None
    assert len(resp.result.artifacts) == 2
    video_art = resp.result.artifacts[0]
    image_art = resp.result.artifacts[1]
    assert Path(video_art.path).exists()
    assert Path(image_art.path).exists()
    assert Path(video_art.path).stat().st_size > 10000
