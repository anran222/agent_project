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


class ChatResponse(BaseModel):
    """Chat response payload."""
    answer: str
    tool: str
    tool_result: str
    user_id: int
