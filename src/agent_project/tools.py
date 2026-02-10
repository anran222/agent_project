from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None


def get_time(args: Dict[str, Any]) -> str:
    timezone = str(args.get("timezone", "Asia/Shanghai"))
    if ZoneInfo is None:
        now = datetime.utcnow()
        return f"Current time (UTC) {now.isoformat()}"
    try:
        now = datetime.now(ZoneInfo(timezone))
    except Exception:
        now = datetime.utcnow()
        return f"Current time (UTC) {now.isoformat()}"
    return f"Current time in {timezone}: {now.isoformat()}"


def run_tool(tool: str, args: Dict[str, Any]) -> str:
    if tool == "get_time":
        return get_time(args)
    return "Unknown tool"


def tool_schema() -> str:
    return "1) get_time(timezone: string) -> string"
