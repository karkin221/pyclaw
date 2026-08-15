"""
Workspace — the folder of plain-text files context assembly reads
(docs/concepts/agent.md, docs/concepts/agent-workspace.md). Same file names
as real OpenClaw's agent workspace:

    AGENTS.md   operating instructions
    SOUL.md     persona / tone
    USER.md     who the user is
    MEMORY.md   curated long-term memory — written only by memory.dream(),
                never edited directly by the assistant mid-conversation
    memory/     episodic daily notes, one file per day, e.g. memory/2026-08-15.md

No token budgets, no truncation limits, no per-agent overrides — real
OpenClaw's bootstrapMaxChars/bootstrapTotalMaxChars and multi-agent workspace
routing are the "engineering" layer this demo intentionally skips.
"""
from datetime import date
from pathlib import Path

BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "USER.md", "MEMORY.md"]


class Workspace:
    def __init__(self, path):
        self.path = Path(path)
        self.memory_dir = self.path / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def read_bootstrap_file(self, name: str) -> str:
        f = self.path / name
        return f.read_text().strip() if f.exists() else ""

    def read_bootstrap_files(self) -> dict:
        return {name: self.read_bootstrap_file(name) for name in BOOTSTRAP_FILES}

    def write_episodic_note(self, session_key: str, user_text: str, reply: str) -> None:
        """Called once per finished turn (see agent_loop.AgentLoop.run). This
        is the ONLY thing that writes during a live turn — mirrors real
        OpenClaw, where the episodic tier is an append-only log and
        MEMORY.md itself is only ever rewritten by dreaming."""
        note_path = self.memory_dir / f"{date.today().isoformat()}.md"
        with note_path.open("a") as f:
            f.write(f"- [{session_key}] user: {user_text}\n")
            f.write(f"- [{session_key}] assistant: {reply}\n")

    def read_episodic_notes(self) -> str:
        notes = sorted(self.memory_dir.glob("*.md"))
        return "\n".join(p.read_text() for p in notes)

    def write_memory_core(self, content: str) -> None:
        (self.path / "MEMORY.md").write_text(content.strip() + "\n")
