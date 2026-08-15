"""
Run the whole diagram, end to end, against a locally running Ollama server
instead of downloading Hugging Face weights — see
openclaw_mini/ollama_model.py for why this exists as a second backend.

    ollama serve                  # in another terminal, if not already running
    ollama pull qwen3:4b          # once
    python main_ollama.py

Identical to main.py — same Gateway, same AgentLoop, same tools, same
memory/dream() call — only the model backend import differs (line 19). No
pip installs beyond the standard library are needed for this path.
"""
from pathlib import Path

from openclaw_mini import memory
from openclaw_mini.gateway import Gateway
from openclaw_mini.ollama_model import DEFAULT_OLLAMA_MODEL, OllamaModelProvider
from openclaw_mini.workspace import Workspace

WORKSPACE_DIR = Path(__file__).parent / "workspace"


def banner(text: str) -> None:
    print(f"\n=== {text} ===")


def main() -> None:
    workspace = Workspace(WORKSPACE_DIR)
    model = OllamaModelProvider(DEFAULT_OLLAMA_MODEL)
    gateway = Gateway(workspace=workspace, model=model)

    banner("Turn 1 — plain question (entry surface -> Gateway -> ①②④)")
    print(gateway.handle_message("demo", "Hi! What can you help me with?"))

    banner("Turn 2 — needs the calculator tool (①②③②④)")
    print(gateway.handle_message("demo", "What is 482 * 17, minus 96?"))

    banner("Turn 3 — delegate to a sub-agent (③b: sessions_spawn)")
    print(
        gateway.handle_message(
            "demo",
            "Delegate this to a sub-agent: explain in one sentence why the sky is blue.",
        )
    )

    banner("Turn 4 — something worth remembering later")
    print(gateway.handle_message("demo", "Please remember that my favorite language is Python."))

    banner("End of session -> dreaming (background memory consolidation)")
    print(memory.dream(workspace, model))

    banner("Turn 5 — a brand NEW session; MEMORY.md should already know")
    print(gateway.handle_message("demo-2", "What's my favorite programming language?"))


if __name__ == "__main__":
    main()
