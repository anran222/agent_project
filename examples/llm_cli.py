from __future__ import annotations

import sys

from agent_project.llm_client import LLMClient


def main() -> int:
    client = LLMClient.from_env()

    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = input("Enter your prompt: ").strip()

    system = "You are a helpful assistant."
    answer = client.generate(prompt=prompt, system=system)
    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
