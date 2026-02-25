"""FastAPI application entrypoint."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from agent_project.app.api.schemas import (
    ChatRequest,
    ChatResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from agent_project.app.services.auth_service import (
    AuthStore,
    User,
    validate_password,
    validate_phone,
)
from agent_project.app.llm.client import LLMClient
from agent_project.app.memory.manager import MemoryManager
from agent_project.app.memory.store import MemoryStore
from agent_project.app.rag.retriever import load_docs, retrieve
from agent_project.app.tools.tools import run_tool, tool_schema

KB_DIR = Path("/Users/a147735/agent_study/agent_project/docs/kb")

app = FastAPI(title="Agent API")

auth_store = AuthStore()


def build_final_prompt(
    memory_context: str,
    rag_context: str,
    user_input: str,
    tool_result: str = "",
) -> str:
    """Build the final prompt from memory, RAG, and tool outputs.

    Args:
        memory_context: Context from memory manager.
        rag_context: Context from RAG retrieval.
        user_input: User message.
        tool_result: Tool output, if any.

    Returns:
        Prompt string.
    """
    sections = []
    if memory_context:
        sections.append("Memory Context:\n" + memory_context)
    if rag_context:
        sections.append("RAG Context:\n" + rag_context)
    if tool_result:
        sections.append("Tool Result:\n" + tool_result)
    sections.append(f"User: {user_input}\nAssistant:")
    return "\n\n".join(sections)


def build_rag_context(query: str) -> str:
    """Retrieve top-k RAG documents and format context.

    Args:
        query: Query text.

    Returns:
        Context string.
    """
    if not KB_DIR.exists():
        return ""
    docs = load_docs(KB_DIR)
    top = retrieve(query, docs, top_k=2)
    if not top:
        return ""
    return "\n\n".join(f"[{doc.doc_id}]\n{doc.text}" for doc, _ in top)


def decide_tool(client: LLMClient, user_input: str) -> dict:
    """Ask the model to decide whether a tool is needed.

    Args:
        client: LLM client.
        user_input: User message.

    Returns:
        Tool decision payload.
    """
    system = (
        "You are a tool-using assistant. "
        "If you need a tool, output ONLY valid JSON: "
        '{"tool": "tool_name", "args": {"key": "value"}}. '
        "If no tool is needed, output ONLY valid JSON: "
        '{"tool": "none", "args": {}}.'
    )
    prompt = (
        "Available tools:\n"
        f"{tool_schema()}\n\n"
        f"User request: {user_input}\n"
        "Respond with JSON only."
    )
    return client.generate_json(prompt=prompt, system=system)


def get_current_user(request: Request) -> User | None:
    """Resolve current user from session cookie.

    Args:
        request: FastAPI request.

    Returns:
        User if authenticated; otherwise None.
    """
    token = request.cookies.get("session_token", "")
    return auth_store.get_user_by_token(token)


@app.post("/auth/register", response_model=UserResponse)
async def register(payload: RegisterRequest, request: Request, response: Response):
    """Register a new user and set a session cookie.

    Args:
        payload: Register payload.
        request: FastAPI request.
        response: FastAPI response.

    Returns:
        User response or error response.
    """
    phone = payload.phone.strip()
    password = payload.password.strip()
    if not validate_phone(phone):
        return JSONResponse({"error": "invalid_phone"}, status_code=400)
    if not validate_password(password):
        return JSONResponse({"error": "weak_password"}, status_code=400)
    if auth_store.user_exists(phone):
        return JSONResponse({"error": "phone_exists"}, status_code=400)
    user = auth_store.create_user(phone, password)
    token = auth_store.create_session(
        user.user_id,
        user_agent=str(request.headers.get("user-agent", "")),
        ip=str(request.client.host if request.client else ""),
    )
    response.set_cookie(
        "session_token",
        token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 72,
    )
    return UserResponse(user_id=user.user_id, phone=user.phone)


@app.post("/auth/login", response_model=UserResponse)
async def login(payload: LoginRequest, request: Request, response: Response):
    """Login user, apply rate limiting, and set session cookie.

    Args:
        payload: Login payload.
        request: FastAPI request.
        response: FastAPI response.

    Returns:
        User response or error response.
    """
    phone = payload.phone.strip()
    password = payload.password.strip()
    allowed, retry_after = auth_store.can_attempt_login(phone)
    if not allowed:
        return JSONResponse({"error": "too_many_attempts", "retry_after": retry_after}, status_code=429)
    user = auth_store.verify_user(phone, password)
    if not user:
        auth_store.record_failed_login(phone)
        return JSONResponse({"error": "invalid_credentials"}, status_code=401)
    auth_store.reset_failed_logins(phone)
    token = auth_store.create_session(
        user.user_id,
        user_agent=str(request.headers.get("user-agent", "")),
        ip=str(request.client.host if request.client else ""),
    )
    response.set_cookie(
        "session_token",
        token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 72,
    )
    return UserResponse(user_id=user.user_id, phone=user.phone)


@app.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout current session.

    Args:
        request: FastAPI request.
        response: FastAPI response.

    Returns:
        Status payload.
    """
    token = request.cookies.get("session_token", "")
    if token:
        auth_store.delete_session(token)
    response.delete_cookie("session_token")
    return {"ok": True}


@app.post("/auth/logout_all")
async def logout_all(request: Request, response: Response):
    """Logout all sessions for the current user.

    Args:
        request: FastAPI request.
        response: FastAPI response.

    Returns:
        Status payload or error response.
    """
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    auth_store.delete_all_sessions(user.user_id)
    response.delete_cookie("session_token")
    return {"ok": True}


@app.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    """Refresh session TTL for the current user.

    Args:
        request: FastAPI request.
        response: FastAPI response.

    Returns:
        Status payload or error response.
    """
    token = request.cookies.get("session_token", "")
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    auth_store.extend_session(token)
    response.set_cookie(
        "session_token",
        token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 72,
    )
    return {"ok": True}


@app.get("/auth/me", response_model=UserResponse)
async def me(request: Request):
    """Return current user info if authenticated.

    Args:
        request: FastAPI request.

    Returns:
        User response or error response.
    """
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return UserResponse(user_id=user.user_id, phone=user.phone)


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request):
    """Non-streaming chat endpoint.

    Args:
        payload: Chat request payload.
        request: FastAPI request.

    Returns:
        Chat response or error response.
    """
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    user_input = payload.message.strip()
    if not user_input:
        return JSONResponse({"error": "empty_message"}, status_code=400)

    client = LLMClient.from_env()
    store = MemoryStore(session_id=str(user.user_id))
    manager = MemoryManager(store=store, llm_client=client)

    memory_context = manager.build_context(user_input)
    rag_context = build_rag_context(user_input)

    tool_result = ""
    tool = "none"
    try:
        decision = decide_tool(client, user_input)
        tool = str(decision.get("tool", "none"))
        args = decision.get("args", {})
        if tool and tool != "none":
            if not isinstance(args, dict):
                args = {}
            tool_result = run_tool(tool, args)
    except Exception:
        tool = "none"
        tool_result = ""

    final_prompt = build_final_prompt(memory_context, rag_context, user_input, tool_result)
    answer = client.generate(prompt=final_prompt, system=None)

    manager.write_from_turn(user_input, answer)
    return ChatResponse(answer=answer, tool=tool, tool_result=tool_result, user_id=user.user_id)


@app.post("/chat/stream")
async def chat_stream(payload: ChatRequest, request: Request):
    """Streaming chat endpoint (SSE).

    Args:
        payload: Chat request payload.
        request: FastAPI request.

    Returns:
        Streaming response or error response.
    """
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    user_input = payload.message.strip()
    if not user_input:
        return JSONResponse({"error": "empty_message"}, status_code=400)

    client = LLMClient.from_env()
    store = MemoryStore(session_id=str(user.user_id))
    manager = MemoryManager(store=store, llm_client=client)

    memory_context = manager.build_context(user_input)
    rag_context = build_rag_context(user_input)

    tool_result = ""
    tool = "none"
    try:
        decision = decide_tool(client, user_input)
        tool = str(decision.get("tool", "none"))
        args = decision.get("args", {})
        if tool and tool != "none":
            if not isinstance(args, dict):
                args = {}
            tool_result = run_tool(tool, args)
    except Exception:
        tool = "none"
        tool_result = ""

    final_prompt = build_final_prompt(memory_context, rag_context, user_input, tool_result)

    def event_stream():
        answer_chunks = []
        for chunk in client.generate_stream(prompt=final_prompt, system=None):
            answer_chunks.append(chunk)
            yield f"data: {json.dumps({'delta': chunk}, ensure_ascii=False)}\n\n"
        answer = "".join(answer_chunks)
        manager.write_from_turn(user_input, answer)
        yield f"data: {json.dumps({'done': True, 'tool': tool, 'tool_result': tool_result}, ensure_ascii=False)}\n\n"

    async def guarded_stream():
        for data in event_stream():
            if await request.is_disconnected():
                break
            yield data

    return StreamingResponse(guarded_stream(), media_type="text/event-stream")
