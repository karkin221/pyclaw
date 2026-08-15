"""
Exercises the ENTIRE system — Gateway, the agent loop, the tool-call loop,
sub-agent delegation, memory writes, and dreaming — with a scripted fake
model instead of a real one. No download, no GPU, a few seconds.

    python sanity_check.py

Use this to confirm the wiring is correct before waiting on a real model
download (`python main.py`), or after you edit the code.
"""
import shutil
import tempfile
from pathlib import Path

from openclaw_mini import memory
from openclaw_mini.gateway import Gateway
from openclaw_mini.mock_model import MockModelProvider
from openclaw_mini.workspace import Workspace

REAL_WORKSPACE = Path(__file__).parent / "workspace"


def main() -> None:
    # Work on a throwaway copy of workspace/ so this never touches your real
    # MEMORY.md or daily notes.
    tmp_dir = Path(tempfile.mkdtemp())
    tmp_workspace_dir = tmp_dir / "workspace"
    shutil.copytree(REAL_WORKSPACE, tmp_workspace_dir)
    workspace = Workspace(tmp_workspace_dir)

    # One scripted line per model call, in the exact order the calls happen:
    # turn 1 (1 call), turn 2 (tool call + final reply = 2 calls), turn 3
    # (spawn call + the child's own reply + the parent's final reply = 3
    # calls), turn 4 (1 call), dream() (1 call) = 8 total.
    model = MockModelProvider(
        [
            "Hi there! I can chat, do arithmetic, delegate work, and remember things.",
            '{"tool": "calculator", "arguments": {"expression": "482 * 17 - 96"}}',
            "482 * 17 - 96 = 8098.",
            '{"tool": "sessions_spawn", "arguments": {"task": "why is the sky blue?"}}',
            "The sky is blue because air scatters short blue wavelengths more than long red ones.",
            "Delegated it — the sky is blue because shorter wavelengths scatter more in the air.",
            "Got it — I'll remember that your favorite language is Python.",
            "- Favorite programming language: Python",
        ]
    )
    gateway = Gateway(workspace=workspace, model=model)

    print("Turn 1 — plain question")
    reply1 = gateway.handle_message("demo", "Hi!")
    print(reply1)
    assert reply1, "expected a non-empty reply"

    print("\nTurn 2 — calculator tool")
    reply2 = gateway.handle_message("demo", "What is 482 * 17 - 96?")
    print(reply2)
    assert "8098" in reply2, "calculator result should reach the final reply"

    print("\nTurn 3 — sub-agent delegation")
    reply3 = gateway.handle_message("demo", "Delegate: why is the sky blue?")
    print(reply3)
    assert "blue" in reply3.lower(), "the sub-agent's answer should come back to the parent"

    print("\nTurn 4 — something to remember")
    reply4 = gateway.handle_message("demo", "Remember my favorite language is Python.")
    print(reply4)

    print("\nEnd of session -> dreaming")
    dream_result = memory.dream(workspace, model)
    print(dream_result)
    assert "python" in dream_result.lower(), "dreaming should have picked up the Python note"

    memory_md = workspace.read_bootstrap_file("MEMORY.md")
    assert "python" in memory_md.lower(), "MEMORY.md should be rewritten on disk after dream()"

    print("\n✅ sanity check passed — every stage ran, and memory made it to disk.")
    shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
