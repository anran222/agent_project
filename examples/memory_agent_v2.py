from __future__ import annotations

import argparse
from pathlib import Path

from agent_project.llm_client import LLMClient
from agent_project.memory_system import MemoryManager, MemoryStore


def build_prompt(context: str, user_input: str) -> str:
    return (
        "You are a helpful assistant with memory. "
        "Use the memory context to answer precisely.\n\n"
        f"Memory Context:\n{context}\n\n"
        f"User: {user_input}\n"
        "Assistant:"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="/Users/a147735/agent_study/agent_project/data/memory.db")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    store = MemoryStore(Path(args.db))
    if args.reset:
        store.reset_all()
        print("Memory cleared.")
        return 0

    client = LLMClient.from_env()
    manager = MemoryManager(store=store, llm_client=client)

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break

        context = manager.build_context(user_input)
        prompt = build_prompt(context, user_input)
        answer = client.generate(prompt=prompt, system=None)
        print(f"Assistant: {answer}")

        manager.write_from_turn(user_input, answer)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
