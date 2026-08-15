"""
Shared console narration for every stage in the diagram. Used by
agent_loop.py (① context assembly, ② model inference, ③ tool execution, ④
reply shaping, on every live turn) and memory.py (the dreaming/memory-
consolidation model call — the same ② stage, running outside a normal
turn) — so `python main.py`/`main_ollama.py`/`run_task.py` narrate every
step in enough detail to trace exactly what happened: which stage ran,
what went to and came back from the model (token counts, and the
reasoning/thinking trace when the model produced one), and every tool
call's arguments and result.

MockModelProvider never sets thinking/input_tokens/output_tokens on a
ModelTurn (see model.py) — trace_tokens below just prints nothing for
those, so sanity_check.py's output is unaffected by any of this.
"""


def stage(label: str, detail: str = "") -> None:
    """Marks entering one box on the diagram."""
    print(f"    · {label}" + (f" — {detail}" if detail else ""))


def trace(label: str, detail: str) -> None:
    """One indented, single-line detail under the current stage."""
    print(f"      ↳ {label}: {detail}")


def trace_block(label: str, text: str) -> None:
    """An indented, multi-line detail under the current stage — for
    anything that can contain newlines (a reasoning trace, tool call
    arguments, a tool result), so it stays visually attached to its label
    instead of breaking the indentation."""
    print(f"      ↳ {label}:")
    for line in text.splitlines() or [""]:
        print(f"        | {line}")


def trace_tokens(turn) -> None:
    """Prints input/output token counts from a ModelTurn when the provider
    reported them (Ollama does via prompt_eval_count/eval_count; the HF
    provider computes them from tensor shapes). Does nothing when neither
    is set."""
    if turn.input_tokens is None and turn.output_tokens is None:
        return
    input_count = turn.input_tokens if turn.input_tokens is not None else "?"
    output_count = turn.output_tokens if turn.output_tokens is not None else "?"
    trace("tokens", f"input={input_count} output={output_count}")
