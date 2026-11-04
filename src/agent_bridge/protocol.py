"""Standard A2A protocol schemas and data models for Agent Bridge."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class AgentId(str, Enum):
    ANTIGRAVITY = "antigravity"
    CODEX = "codex"
    CLAUDE = "claude"


class TaskType(str, Enum):
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"
    CODE_EXECUTION = "code_execution"
    CODE_REVIEW = "code_review"
    GENERAL_CHAT = "general_chat"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentCapability(BaseModel):
    name: str = Field(..., description="Capability identifier, e.g. image_generation")
    description: str = Field(..., description="Human-readable capability description")


class AgentDescriptor(BaseModel):
    agent_id: str = Field(..., description="Unique agent identifier (antigravity, codex, claude)")
    display_name: str = Field(..., description="Display name of the agent")
    status: str = Field(default="online", description="online, degraded, or offline")
    backend_mode: str = Field(..., description="How the daemon invokes this agent (e.g. agentapi, cli, sdk)")
    capabilities: list[str] = Field(default_factory=list, description="Supported task types/capabilities")
    description: str = Field(default="", description="Detailed strengths and specialties of this agent")


class ArtifactItem(BaseModel):
    type: str = Field(..., description="Artifact type: image, video, file, text")
    path: str = Field(..., description="Absolute path to the generated file on disk")
    mime_type: str = Field(default="application/octet-stream", description="MIME type of the artifact")
    description: str = Field(default="", description="Optional caption or description")


class TaskResultPayload(BaseModel):
    summary: str = Field(..., description="Concise summary of the completed task")
    artifacts: list[ArtifactItem] = Field(default_factory=list, description="Generated files (images, videos, etc.)")
    raw_output: str = Field(default="", description="Full text response or logs from the worker agent")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra execution metadata")


class AgentTaskRequest(BaseModel):
    caller_agent: str = Field(default="unknown", description="ID of the calling agent (e.g. codex, claude, antigravity)")
    target_agent: str = Field(..., description="ID of the target agent to invoke (antigravity, codex, claude)")
    task_type: str = Field(default=TaskType.GENERAL_CHAT.value, description="Type of task to execute")
    prompt: str = Field(..., description="Detailed instruction or prompt for the target agent")
    output_dir: str | None = Field(default=None, description="Directory where generated files should be saved")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional parameters (aspect_ratio, duration_sec, filename_prefix, model, etc.)",
    )
    context: dict[str, Any] = Field(default_factory=dict, description="Optional workspace/file context")
    hop_count: int = Field(default=0, ge=0, description="Current A2A hop count for loop prevention")
    max_hops: int = Field(default=3, ge=1, le=10, description="Maximum allowed hops before firewall rejection")
    call_chain: list[str] = Field(default_factory=list, description="Ordered list of agents in the current call chain")
    async_mode: bool = Field(default=False, description="If true, enqueue and return task_id immediately")


class AgentTaskResponse(BaseModel):
    task_id: str = Field(..., description="Unique task identifier")
    status: TaskStatus = Field(..., description="Current status of the task")
    caller_agent: str = Field(..., description="Originating caller agent")
    target_agent: str = Field(..., description="Target worker agent")
    task_type: str = Field(..., description="Task type")
    hop_count: int = Field(..., description="Incremented hop count")
    call_chain: list[str] = Field(default_factory=list, description="Updated call chain")
    result: TaskResultPayload | None = Field(default=None, description="Task result payload when completed")
    error: str | None = Field(default=None, description="Error message if status is failed")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 creation timestamp",
    )
    completed_at: str | None = Field(default=None, description="ISO 8601 completion timestamp")
