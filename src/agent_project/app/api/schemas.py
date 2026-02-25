"""Pydantic request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """Register request payload."""
    phone: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    """Login request payload."""
    phone: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    """User response payload."""
    user_id: int
    phone: str


class ChatRequest(BaseModel):
    """Chat request payload."""
    message: str = Field(..., min_length=1)
    session_id: int | None = None


class ChatResponse(BaseModel):
    """Chat response payload."""
    answer: str
    tool: str
    tool_result: str
    user_id: int
    session_id: int


class SessionCreateRequest(BaseModel):
    """Create session request payload."""

    title: str = Field(default="新会话", min_length=1, max_length=255)


class SessionRenameRequest(BaseModel):
    """Rename session request payload."""

    title: str = Field(..., min_length=1, max_length=255)


class SessionResponse(BaseModel):
    """Session response payload."""

    session_id: int
    title: str
    last_message_preview: str
    created_at: str
    updated_at: str


class SessionMessageResponse(BaseModel):
    """Session message response payload."""

    message_id: int
    session_id: int
    role: str
    content: str
    created_at: str
