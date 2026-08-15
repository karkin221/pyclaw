"""
Dreaming — the background box on the diagram, and the one part of the loop
that is NOT triggered by an incoming message. Real OpenClaw runs this on a
schedule, and every candidate first has to pass a deterministic provenance
gate that structurally excludes anything tagged "untrusted" or "system"
before a model ever sees it (docs/concepts/memory-architecture.md) — that
gate is the actual security boundary of the real system, and it's the piece
this demo leaves out, since a single-user demo has nothing untrusted to
filter. What's left is the part underneath the gate: read what happened,
ask the model to fold it into the curated file, save the result.
"""
from .trace import stage, trace_block, trace_tokens

DREAM_SYSTEM_PROMPT = """\
You maintain one short long-term memory file for a personal assistant.
You'll be given the current file and a batch of new daily notes. Rewrite
the file: merge in anything durable and worth remembering long term, update
or drop anything the new notes contradict, and leave out anything trivial
or one-off. Reply with ONLY the new file's contents, as short bullet
points."""


def dream(workspace, model) -> str:
    notes = workspace.read_episodic_notes()
    if not notes.strip():
        return "(nothing new to consolidate)"

    stage("💭 Dreaming — memory consolidation")
    existing = workspace.read_bootstrap_file("MEMORY.md") or "(empty)"
    user_prompt = f"# Current MEMORY.md\n{existing}\n\n# New daily notes\n{notes}"

    turn = model.infer(
        [
            {"role": "system", "content": DREAM_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )
    trace_tokens(turn)
    if turn.thinking:
        trace_block("thinking", turn.thinking)
    workspace.write_memory_core(turn.text)
    return turn.text
