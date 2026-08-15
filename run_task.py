"""
Give the loop one real, open-ended task instead of the canned demo turns in
main.py/main_ollama.py, and see how far it gets — same Gateway/AgentLoop/
tools/memory code, just a single substantial prompt instead of a scripted
conversation.

    ollama serve                     # if not already running
    ollama pull qwen3:4b             # once
    python run_task.py               # runs the built-in example task
    python run_task.py "some other task, however long"

Tasks like this usually need more than the demos' MAX_TOOL_HOPS=4 (see
agent_loop.py) to get anywhere — this script raises the ceiling just for
itself via Gateway(max_tool_hops=...), without touching the default the
other entry points rely on. Raise MAX_TOOL_HOPS below if the model runs
out of room (you'll see "I couldn't finish that within this demo's
tool-call limit" if it does).

Files the model saves with the `write_file` tool land in workspace/,
alongside the agent's own AGENTS.md/SOUL.md/USER.md/MEMORY.md — this
script diffs workspace/ before and after and prints whatever's new.
"""
import sys
import time
from pathlib import Path

from openclaw_mini.gateway import Gateway
from openclaw_mini.ollama_model import DEFAULT_OLLAMA_MODEL, OllamaModelProvider
from openclaw_mini.workspace import Workspace

WORKSPACE_DIR = Path(__file__).parent / "workspace"

MAX_TOOL_HOPS = 20  # generous — this is a stress test, not the demo path

DEFAULT_TASK = """\
Implement an A* pathfinding visualizer.
Requirements:
- Tkinter GUI
- Interactive obstacle placement
- Adjustable grid size
- Step-by-step visualization
- Compare BFS, Dijkstra, and A*
- Benchmark each algorithm on random maps
- Produce a markdown report summarizing runtime results."""

# Bootstrap files that always live in workspace/ — not "output" from this run.
BOOTSTRAP_NAMES = {"AGENTS.md", "SOUL.md", "USER.md", "MEMORY.md"}


def snapshot(workspace_dir: Path) -> dict[str, float]:
    """path (relative to workspace/) -> mtime, for everything except the
    bootstrap files and episodic notes under memory/ — so a before/after
    diff shows only what this run actually produced."""
    files = {}
    for path in workspace_dir.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(workspace_dir)
        if "memory" in rel.parts or path.name in BOOTSTRAP_NAMES:
            continue
        files[str(rel)] = path.stat().st_mtime
    return files


def main() -> None:
    task = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TASK

    workspace = Workspace(WORKSPACE_DIR)
    model = OllamaModelProvider(DEFAULT_OLLAMA_MODEL)
    gateway = Gateway(workspace=workspace, model=model, max_tool_hops=MAX_TOOL_HOPS)

    before = snapshot(WORKSPACE_DIR)

    print(f"=== Task (max {MAX_TOOL_HOPS} tool hops, model {DEFAULT_OLLAMA_MODEL}) ===")
    print(task)
    print()

    start = time.monotonic()
    reply = gateway.handle_message("task-run", task)
    elapsed = time.monotonic() - start

    print(f"\n=== Final reply ({elapsed:.1f}s) ===")
    print(reply)

    after = snapshot(WORKSPACE_DIR)
    changed = sorted(name for name, mtime in after.items() if before.get(name) != mtime)

    print("\n=== Files written to workspace/ ===")
    if changed:
        for name in changed:
            print(f"  workspace/{name}")
    else:
        print("  (none — the model never called write_file)")


if __name__ == "__main__":
    main()
