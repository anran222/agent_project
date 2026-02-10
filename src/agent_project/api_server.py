from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict

from agent_project.llm_client import LLMClient
from agent_project.memory_system import MemoryManager, MemoryStore
from agent_project.rag_retriever import load_docs, retrieve
from agent_project.tools import run_tool, tool_schema

KB_DIR = Path("/Users/a147735/agent_study/agent_project/docs/kb")
DB_PATH = Path("/Users/a147735/agent_study/agent_project/data/memory.db")


def build_final_prompt(memory_context: str, rag_context: str, user_input: str, tool_result: str = "") -> str:
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
    if not KB_DIR.exists():
        return ""
    docs = load_docs(KB_DIR)
    top = retrieve(query, docs, top_k=2)
    if not top:
        return ""
    return "\n\n".join(f"[{doc.doc_id}]\n{doc.text}" for doc, _ in top)


def decide_tool(client: LLMClient, user_input: str) -> Dict[str, Any]:
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


class AgentHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: Dict[str, Any]) -> None:
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self) -> None:
        if self.path != "/chat":
            self._send(404, {"error": "not_found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            self._send(400, {"error": "invalid_json"})
            return

        user_input = str(payload.get("message", "")).strip()
        session_id = str(payload.get("session_id", "default")).strip() or "default"
        if not user_input:
            self._send(400, {"error": "empty_message"})
            return

        client = LLMClient.from_env()
        store = MemoryStore(DB_PATH, session_id=session_id)
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

        final_prompt = build_final_prompt(
            memory_context, rag_context, user_input, tool_result
        )
        answer = client.generate(prompt=final_prompt, system=None)

        manager.write_from_turn(user_input, answer)
        self._send(
            200,
            {
                "answer": answer,
                "tool": tool,
                "tool_result": tool_result,
                "session_id": session_id,
            },
        )


def run(host: str = "127.0.0.1", port: int = 8080) -> None:
    server = HTTPServer((host, port), AgentHandler)
    print(f"Agent API running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
