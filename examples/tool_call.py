from __future__ import annotations

import json
from typing import Any, Dict

from agent_project.app.llm.client import LLMClient


def get_time(args: Dict[str, Any]) -> str:
    timezone = args.get("timezone", "local")
    return f"Current time in {timezone}: 10:00"  # placeholder


def run_tool(tool: str, args: Dict[str, Any]) -> str:
    if tool == "get_time":
        return get_time(args)
    return "Unknown tool"


def main() -> int:
    system = (
        "You are a tool-using assistant. "
        "Decide whether to call a tool. "
        "If you need a tool, output ONLY valid JSON: "
        '{"tool": "tool_name", "args": {"key": "value"}}. '
        "If no tool is needed, output ONLY valid JSON: "
        '{"tool": "none", "args": {}}.'
    )

    user = input("User request: ").strip()
    prompt = (
        "Available tools:\n"
        "1) get_time(timezone: string) -> string\n\n"
        f"User request: {user}\n"
        "Respond with JSON only."
    )

    client = LLMClient.from_env()
    decision = client.generate_json(prompt=prompt, system=system)
    
    print(f"LLM决策结果: {decision}")  # 调试信息

    tool = decision.get("tool", "none")
    args = decision.get("args", {})

    if tool == "none":
        print("No tool needed. Model response:", json.dumps(decision))
        return 0

    result = run_tool(tool, args)
    print("Tool result:", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
