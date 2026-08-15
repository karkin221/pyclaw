"""
Run the whole diagram, end to end, with a real small open-weights model.

    pip install -r requirements.txt
    python main.py

First run downloads the model from Hugging Face (~1-3GB depending on which
one — see openclaw_mini/model.py), so it needs a normal internet connection
and a minute or two. After that it's cached locally and starts instantly.

No download yet, or just want to check the wiring first? Run
`python sanity_check.py` instead — same code path, a scripted fake model,
done in seconds.
"""
from pathlib import Path

from openclaw_mini import memory
from openclaw_mini.gateway import Gateway
from openclaw_mini.model import DEFAULT_MODEL, ModelProvider
from openclaw_mini.workspace import Workspace

WORKSPACE_DIR = Path(__file__).parent / "workspace"


def banner(text: str) -> None:
    print(f"\n=== {text} ===")


def main() -> None:
    workspace = Workspace(WORKSPACE_DIR)
    model = ModelProvider(DEFAULT_MODEL)
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
