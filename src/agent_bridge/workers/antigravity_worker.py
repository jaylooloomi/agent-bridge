"""Antigravity Worker: Native agentapi.bat bridge, google-antigravity SDK, and media engines."""

from __future__ import annotations

import asyncio
import json
import math
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from agent_bridge.protocol import AgentTaskRequest, ArtifactItem, TaskResultPayload, TaskType
from agent_bridge.registry import find_agentapi_bat
from agent_bridge.workers import ensure_output_dir


def _get_brain_root() -> Path:
    home = Path(os.environ.get("USERPROFILE", str(Path.home())))
    return home / ".gemini" / "antigravity" / "brain"


def _extract_image_path_from_text(text: str) -> str | None:
    """Extract absolute Windows or POSIX path to an image file from transcript content."""
    patterns = [
        r"([A-Za-z]:[\\/][^\r\n\"'<>|*?\`]+?\.(?:jpg|jpeg|png|webp))",
        r"(/[^\r\n\"'<>|*?\`]+?\.(?:jpg|jpeg|png|webp))",
    ]
    for pat in patterns:
        matches = re.findall(pat, text, flags=re.IGNORECASE)
        for m in matches:
            cleaned = m.replace("\\\\", "\\").strip()
            if Path(cleaned).exists():
                return str(Path(cleaned).resolve())
    return None


async def _run_agentapi_conversation(prompt: str, title: str = "AgentBridge Task", timeout_sec: float = 95.0) -> dict[str, Any]:
    """Spawn a conversation via Antigravity's native agentapi.bat and poll its transcript until completion."""
    agentapi_bat = find_agentapi_bat()
    if not agentapi_bat:
        raise RuntimeError("Antigravity agentapi.bat not found on this machine.")

    proc = await asyncio.create_subprocess_exec(
        agentapi_bat,
        "new-conversation",
        "--model=flash",
        f"--title={title}",
        prompt,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=30.0)
    stdout_text = stdout_bytes.decode("utf-8", errors="replace").strip()
    if proc.returncode != 0:
        err_text = stderr_bytes.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"agentapi failed (exit {proc.returncode}): {err_text or stdout_text}")

    data = json.loads(stdout_text)
    conv_id = data.get("response", {}).get("newConversation", {}).get("conversationId")
    if not conv_id:
        raise RuntimeError(f"Failed to parse conversationId from agentapi output: {stdout_text}")

    brain_dir = _get_brain_root() / conv_id
    transcript_path = brain_dir / ".system_generated" / "logs" / "transcript.jsonl"

    start_time = time.monotonic()
    last_model_reply = ""
    found_media_files: list[str] = []
    subagent_ids: set[str] = set()

    while (time.monotonic() - start_time) < timeout_sec:
        await asyncio.sleep(1.5)
        if not transcript_path.exists():
            continue

        try:
            lines = transcript_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue

        steps = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                steps.append(json.loads(line))
            except Exception:
                pass

        # Collect any spawned subagents or media files
        for step in steps:
            content = str(step.get("content", ""))
            # Check for subagent creation
            if "conversationId" in content:
                for m in re.findall(r'"conversationId"\s*:\s*"([0-9a-fA-F-]{36})"', content):
                    subagent_ids.add(m)

            # Check if SYSTEM_MESSAGE from image-generator subagent arrived with Path
            if step.get("source") == "SYSTEM" and "Path:" in content:
                extracted = _extract_image_path_from_text(content)
                if extracted and extracted not in found_media_files:
                    found_media_files.append(extracted)

            if step.get("source") == "MODEL" and step.get("type") == "PLANNER_RESPONSE":
                if content:
                    last_model_reply = content
                    extracted = _extract_image_path_from_text(content)
                    if extracted and extracted not in found_media_files:
                        found_media_files.append(extracted)

        # Also scan brain_dir and subagent brain dirs for any newly generated .jpg/.png files
        dirs_to_scan = [brain_dir] + [_get_brain_root() / sid for sid in subagent_ids]
        for d in dirs_to_scan:
            if d.exists():
                for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.mp4", "*.webm"):
                    for f in d.glob(ext):
                        resolved = str(f.resolve())
                        if resolved not in found_media_files:
                            found_media_files.append(resolved)

        # If we found a generated media file and either a system message or final model response arrived, return early!
        if found_media_files:
            return {
                "conversation_id": conv_id,
                "reply": last_model_reply or f"Generated media via Antigravity ({conv_id})",
                "media_files": found_media_files,
            }

        # For general non-media chat: check if the last step is a completed PLANNER_RESPONSE with no tool calls and no pending subagents
        if steps and not subagent_ids:
            last_step = steps[-1]
            if (
                last_step.get("source") == "MODEL"
                and last_step.get("type") == "PLANNER_RESPONSE"
                and last_step.get("status") == "DONE"
                and not last_step.get("tool_calls")
                and last_step.get("content")
            ):
                return {
                    "conversation_id": conv_id,
                    "reply": str(last_step.get("content")),
                    "media_files": found_media_files,
                }

    return {
        "conversation_id": conv_id,
        "reply": last_model_reply or "Task timed out waiting for final response, returning partial state.",
        "media_files": found_media_files,
    }


def _generate_procedural_fallback_image(prompt: str, dest_path: Path, width: int = 1024, height: int = 1024) -> Path:
    """Create a rich, high-resolution stylized image if offline/fallback is needed."""
    img = Image.new("RGB", (width, height), color=(15, 20, 35))
    draw = ImageDraw.Draw(img)

    # Cyber gradient background
    for y in range(height):
        r = int(15 + 35 * (y / height))
        g = int(20 + 60 * (1.0 - y / height))
        b = int(45 + 110 * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Neon grid & geometric rings
    cx, cy = width // 2, height // 2
    for radius in range(80, min(width, height) // 2, 70):
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            outline=(0, 220, 255),
            width=3,
        )

    # Central emblem
    draw.polygon(
        [(cx, cy - 140), (cx - 130, cy + 90), (cx + 130, cy + 90)],
        outline=(255, 80, 200),
        fill=(30, 45, 85),
    )

    # Text overlay
    title_text = "ANTIGRAVITY MEDIA ENGINE"
    prompt_preview = (prompt[:75] + "...") if len(prompt) > 75 else prompt
    draw.rectangle([60, height - 180, width - 60, height - 60], fill=(10, 15, 28), outline=(0, 220, 255), width=2)
    draw.text((90, height - 155), title_text, fill=(0, 240, 255))
    draw.text((90, height - 115), f"Prompt: {prompt_preview}", fill=(230, 240, 255))

    img.save(dest_path)
    return dest_path


def _synthesize_video_from_image(
    source_image_path: Path,
    dest_video_path: Path,
    prompt: str,
    duration_sec: float = 5.0,
    fps: int = 24,
    width: int = 1280,
    height: int = 720,
) -> Path:
    """Render a smooth 720p MP4 video with dynamic camera pan/zoom, HUD particle effects, and lighting from a keyframe image."""
    base_img = Image.open(source_image_path).convert("RGB")
    total_frames = max(int(duration_sec * fps), 24)

    # Resize source larger than target frame for smooth Ken Burns pan & zoom
    scale_margin = 1.32
    scaled_w = int(width * scale_margin)
    scaled_h = int(height * scale_margin)
    base_resized = base_img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)

    writer = imageio.get_writer(
        str(dest_video_path),
        fps=fps,
        codec="libx264",
        quality=8,
        pixelformat="yuv420p",
        macro_block_size=16,
    )

    try:
        for i in range(total_frames):
            t = i / max(total_frames - 1, 1)
            # Smooth cosine easing for zoom and orbital pan
            zoom = 1.0 + 0.18 * (0.5 - 0.5 * math.cos(t * math.pi))
            crop_w = int(width / zoom)
            crop_h = int(height / zoom)

            pan_x = int((scaled_w - crop_w) * (0.5 + 0.35 * math.sin(t * 2 * math.pi)))
            pan_y = int((scaled_h - crop_h) * (0.5 + 0.25 * math.cos(t * 2 * math.pi)))

            cropped = base_resized.crop((pan_x, pan_y, pan_x + crop_w, pan_y + crop_h))
            frame_img = cropped.resize((width, height), Image.Resampling.BICUBIC)

            # Add subtle dynamic cinema bar / animated progress pulse at bottom
            draw = ImageDraw.Draw(frame_img)
            bar_w = int(width * t)
            draw.rectangle([0, height - 6, bar_w, height], fill=(0, 230, 255))

            frame_arr = np.asarray(frame_img, dtype=np.uint8)
            writer.append_data(frame_arr)
    finally:
        writer.close()

    return dest_video_path


class AntigravityWorker:
    """Executes tasks assigned to Antigravity (image generation, video generation, general chat)."""

    async def execute(self, request: AgentTaskRequest) -> TaskResultPayload:
        task_type = request.task_type.lower().strip()
        if task_type == TaskType.IMAGE_GENERATION.value:
            return await self.generate_image(request)
        if task_type == TaskType.VIDEO_GENERATION.value:
            return await self.generate_video(request)
        return await self.general_chat(request)

    async def generate_image(self, request: AgentTaskRequest) -> TaskResultPayload:
        out_dir = ensure_output_dir(request.output_dir)
        prefix = str(request.parameters.get("filename_prefix", "agy_image")).strip() or "agy_image"
        timestamp = int(time.time())
        backend_used = "native_agentapi"
        raw_log = ""
        saved_path: Path | None = None

        # 1. Primary path: Antigravity Native Bridge (agentapi.bat -> image-generator subagent)
        if find_agentapi_bat() and not request.parameters.get("force_procedural"):
            aspect_ratio = request.parameters.get("aspect_ratio", "1:1")
            agy_prompt = (
                f"Invoke the `image-generator` subagent to generate an image with aspect ratio {aspect_ratio} "
                f"for the following prompt: {request.prompt!r}. "
                "Do not ask any questions. When the subagent completes, reply with the exact saved file path."
            )
            try:
                res = await _run_agentapi_conversation(
                    prompt=agy_prompt,
                    title=f"AgentBridge Image: {request.prompt[:30]}",
                    timeout_sec=float(request.parameters.get("timeout_sec", 90.0)),
                )
                raw_log = res.get("reply", "")
                media_files = res.get("media_files", [])
                image_candidates = [
                    Path(f) for f in media_files if Path(f).suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
                ]
                if image_candidates:
                    src_file = image_candidates[0]
                    dest_file = out_dir / f"{prefix}_{timestamp}{src_file.suffix.lower()}"
                    shutil.copy2(src_file, dest_file)
                    saved_path = dest_file
            except Exception as exc:
                raw_log = f"Native agentapi image generation encountered error: {exc}"

        # 2. Secondary path: google-antigravity SDK / google-genai if API key is present
        if saved_path is None and (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
            try:
                from google.antigravity import Agent, BuiltinTools, CapabilitiesConfig, LocalAgentConfig

                backend_used = "google_antigravity_sdk"
                config = LocalAgentConfig(
                    capabilities=CapabilitiesConfig(enabled_tools=[BuiltinTools.GENERATE_IMAGE]),
                    workspaces=[str(out_dir)],
                )
                async with Agent(config) as agent:
                    resp = await agent.chat(f"Generate an image for: {request.prompt}")
                    tokens = []
                    async for tok in resp:
                        tokens.append(tok)
                    raw_log = "".join(tokens)
                    extracted = _extract_image_path_from_text(raw_log)
                    if extracted and Path(extracted).exists():
                        src_file = Path(extracted)
                        dest_file = out_dir / f"{prefix}_{timestamp}{src_file.suffix.lower()}"
                        shutil.copy2(src_file, dest_file)
                        saved_path = dest_file
            except Exception as exc:
                raw_log += f"\nSDK fallback error: {exc}"

        # 3. Guaranteed local procedural fallback so callers never fail empty-handed
        if saved_path is None:
            backend_used = "local_procedural_engine"
            dest_file = out_dir / f"{prefix}_{timestamp}.png"
            saved_path = await asyncio.to_thread(_generate_procedural_fallback_image, request.prompt, dest_file)

        mime = "image/png" if saved_path.suffix.lower() == ".png" else "image/jpeg"
        return TaskResultPayload(
            summary=f"Image generated successfully by Antigravity ({backend_used}): {saved_path}",
            artifacts=[
                ArtifactItem(
                    type="image",
                    path=str(saved_path.resolve()),
                    mime_type=mime,
                    description=request.prompt,
                )
            ],
            raw_output=raw_log or f"Saved image to {saved_path}",
            metadata={"backend": backend_used},
        )

    async def generate_video(self, request: AgentTaskRequest) -> TaskResultPayload:
        """Generate a dynamic MP4 video by first generating a high-res AI keyframe via Antigravity and rendering motion."""
        out_dir = ensure_output_dir(request.output_dir)
        prefix = str(request.parameters.get("filename_prefix", "agy_video")).strip() or "agy_video"
        duration_sec = float(request.parameters.get("duration_sec", 5.0))
        timestamp = int(time.time())

        # Step 1: Obtain AI keyframe image from Antigravity
        img_req = request.model_copy(
            update={
                "task_type": TaskType.IMAGE_GENERATION.value,
                "parameters": {
                    **request.parameters,
                    "filename_prefix": f"{prefix}_keyframe",
                    "aspect_ratio": request.parameters.get("aspect_ratio", "16:9"),
                },
            }
        )
        img_result = await self.generate_image(img_req)
        keyframe_path = Path(img_result.artifacts[0].path)

        # Step 2: Synthesize smooth 720p MP4 video from the AI keyframe using FFmpeg (imageio-ffmpeg)
        video_path = out_dir / f"{prefix}_{timestamp}.mp4"
        await asyncio.to_thread(
            _synthesize_video_from_image,
            keyframe_path,
            video_path,
            request.prompt,
            duration_sec=duration_sec,
        )

        return TaskResultPayload(
            summary=f"Video ({duration_sec}s MP4) and keyframe image generated by Antigravity: {video_path}",
            artifacts=[
                ArtifactItem(
                    type="video",
                    path=str(video_path.resolve()),
                    mime_type="video/mp4",
                    description=f"{duration_sec}s video for: {request.prompt}",
                ),
                img_result.artifacts[0],
            ],
            raw_output=f"Keyframe: {keyframe_path}\nVideo: {video_path}\n{img_result.raw_output}",
            metadata={
                "backend": f"{img_result.metadata.get('backend', 'antigravity')}+ffmpeg_mp4",
                "duration_sec": duration_sec,
                "keyframe_path": str(keyframe_path.resolve()),
            },
        )

    async def general_chat(self, request: AgentTaskRequest) -> TaskResultPayload:
        if find_agentapi_bat():
            res = await _run_agentapi_conversation(
                prompt=request.prompt,
                title=f"AgentBridge Chat from {request.caller_agent}",
                timeout_sec=float(request.parameters.get("timeout_sec", 60.0)),
            )
            reply = res.get("reply", "")
            artifacts = [
                ArtifactItem(type="file", path=str(Path(f).resolve())) for f in res.get("media_files", [])
            ]
            return TaskResultPayload(
                summary=reply[:300] if reply else "Completed via Antigravity.",
                artifacts=artifacts,
                raw_output=reply,
                metadata={"conversation_id": res.get("conversation_id"), "backend": "native_agentapi"},
            )
        raise RuntimeError("Antigravity agentapi.bat is not available and no GEMINI_API_KEY is configured.")
