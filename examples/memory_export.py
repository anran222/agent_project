from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_project.app.memory.store import MemoryStore


def export_json(store: MemoryStore, out_path: Path) -> None:
    data = {
        "messages": [m.__dict__ for m in store.recent_messages(limit=10_000)],
        "memory_items": [m.__dict__ for m in store.list_memory_items()],
        "summary": store.latest_summary() or "",
        "profile": store.get_profile(),
        "tasks": [
            {"title": t[0], "notes": t[1]} for t in store.list_open_tasks(limit=10_000)
        ],
    }
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def export_markdown(store: MemoryStore, out_path: Path) -> None:
    lines = []
    lines.append("# Memory Report\n")
    profile = store.get_profile()
    if profile:
        lines.append("## User Profile")
        for k, v in profile.items():
            lines.append(f"- {k}: {v}")
        lines.append("")

    summary = store.latest_summary() or ""
    if summary:
        lines.append("## Conversation Summary")
        lines.append(summary)
        lines.append("")

    tasks = store.list_open_tasks(limit=50)
    if tasks:
        lines.append("## Open Tasks")
        for title, notes in tasks:
            if notes:
                lines.append(f"- {title} ({notes})")
            else:
                lines.append(f"- {title}")
        lines.append("")

    memories = store.list_memory_items()
    if memories:
        lines.append("## Long-term Memory")
        for item in memories:
            lines.append(f"- [{item.mem_type}] {item.content} (importance={item.importance})")
        lines.append("")

    messages = store.recent_messages(limit=50)
    if messages:
        lines.append("## Recent Messages")
        for m in messages:
            lines.append(f"- {m.role}: {m.content}")
        lines.append("")

    out_path.write_text("\n".join(lines))


def export_html(store: MemoryStore, out_path: Path) -> None:
    profile = store.get_profile()
    summary = store.latest_summary() or ""
    tasks = store.list_open_tasks(limit=50)
    memories = store.list_memory_items()
    messages = store.recent_messages(limit=50)

    def li(items):
        return "\n".join(items) if items else "<li>None</li>"

    html = f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>Memory Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    h2 {{ margin-top: 24px; }}
    ul {{ line-height: 1.6; }}
    .section {{ padding: 12px 16px; background: #f7f7f7; border-radius: 8px; }}
  </style>
</head>
<body>
  <h1>Memory Report</h1>
  <div class=\"section\">
    <h2>User Profile</h2>
    <ul>
      {li([f'<li>{k}: {v}</li>' for k, v in profile.items()])}
    </ul>
  </div>
  <div class=\"section\">
    <h2>Conversation Summary</h2>
    <p>{summary or 'None'}</p>
  </div>
  <div class=\"section\">
    <h2>Open Tasks</h2>
    <ul>
      {li([f'<li>{t} ({n})</li>' if n else f'<li>{t}</li>' for t, n in tasks])}
    </ul>
  </div>
  <div class=\"section\">
    <h2>Long-term Memory</h2>
    <ul>
      {li([f'<li>[{m.mem_type}] {m.content} (importance={m.importance})</li>' for m in memories])}
    </ul>
  </div>
  <div class=\"section\">
    <h2>Recent Messages</h2>
    <ul>
      {li([f'<li>{m.role}: {m.content}</li>' for m in messages])}
    </ul>
  </div>
</body>
</html>
"""
    out_path.write_text(html)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", default="default")
    parser.add_argument("--out", required=True, help="Output file path (.json/.md/.html)")
    args = parser.parse_args()

    store = MemoryStore(session_id=args.session)
    out_path = Path(args.out)
    if out_path.suffix == ".json":
        export_json(store, out_path)
    elif out_path.suffix == ".md":
        export_markdown(store, out_path)
    elif out_path.suffix == ".html":
        export_html(store, out_path)
    else:
        raise ValueError("Unsupported output format. Use .json/.md/.html")

    print(f"Exported: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
