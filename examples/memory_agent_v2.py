from __future__ import annotations

import argparse

from agent_project.app.llm.client import LLMClient
from agent_project.app.memory.store import MemoryStore
from agent_project.app.memory.manager import MemoryManager


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
    parser.add_argument("--session", default="default")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    store = MemoryStore(session_id=args.session)
    if args.reset:
        store.reset_all()
        print("Memory cleared.")
        return 0

    manager = MemoryManager(store=store, llm_client=LLMClient.from_env())

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break

        context = manager.build_context(user_input)
        prompt = build_prompt(context, user_input)
        answer = manager.llm_client.generate(prompt=prompt, system=None)
        print(f"Assistant: {answer}")

        manager.write_from_turn(user_input, answer)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
