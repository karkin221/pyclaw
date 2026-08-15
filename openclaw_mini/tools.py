"""
Tools — diagram stage "③ Tool execution", plus the sessions_spawn tool that
stage ③b (sub-agent delegation) is built from.

Real OpenClaw checks tool policy (allow/deny per agent/channel/sender), runs
before_tool_call/after_tool_call plugin hooks, and can run the call inside a
Docker/SSH/OpenShell sandbox (docs/gateway/sandboxing.md). None of that is
here — a tool call just calls the matching Python function directly. That's
the main piece of "engineering" this demo strips out; see the README table
for the full list.
"""
from __future__ import annotations

import ast
import json
import operator
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ToolCall:
    name: str
    arguments: dict


@dataclass
class ToolContext:
    """Everything a tool call needs about the world it's running in, passed
    to every tool the same way. `gateway` is what makes sessions_spawn
    possible: the tool calls straight back into the same Gateway that
    dispatched it, to start a brand new session."""

    workspace: "Workspace"
    gateway: "Gateway"
    depth: int = 0


# ---- calculator: a safe arithmetic evaluator, not a raw eval() -----------

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("only plain arithmetic (+ - * / % **) is allowed")


def calculator(arguments: dict, ctx: ToolContext) -> str:
    expression = arguments.get("expression", "")
    try:
        return str(_safe_eval(ast.parse(expression, mode="eval")))
    except Exception as exc:
        return f"error: could not evaluate {expression!r} ({exc})"


# ---- file tools, kept inside the workspace directory ----------------------


def _resolve_inside_workspace(ctx: ToolContext, raw_path: str) -> Path | None:
    candidate = (ctx.workspace.path / raw_path).resolve()
    try:
        candidate.relative_to(ctx.workspace.path.resolve())
    except ValueError:
        return None
    return candidate


def read_file(arguments: dict, ctx: ToolContext) -> str:
    path = _resolve_inside_workspace(ctx, arguments.get("path", ""))
    if path is None:
        return "error: path escapes the workspace"
    return path.read_text() if path.exists() else "error: file not found"


def write_file(arguments: dict, ctx: ToolContext) -> str:
    path = _resolve_inside_workspace(ctx, arguments.get("path", ""))
    if path is None:
        return "error: path escapes the workspace"
    path.write_text(arguments.get("content", ""))
    return f"wrote {path.name}"


# ---- sessions_spawn: sub-agent delegation, stage ③b -----------------------


def sessions_spawn(arguments: dict, ctx: ToolContext) -> str:
    """Real OpenClaw's sessions_spawn is non-blocking: it returns instantly
    and the child *announces* its result back later, whenever it finishes
    (docs/tools/subagents.md). Reproducing that push-based delivery needs a
    queue and an event loop — exactly the "engineering" this demo strips
    out. Here sessions_spawn just blocks: spawn a child session, run its
    entire agent loop to completion right now, and hand its reply straight
    back as this tool's result.

    Real OpenClaw also allows up to 5 levels of sub-agent nesting
    (maxSpawnDepth). This demo caps it at 1 to keep the call graph easy to
    read on a first pass.
    """
    if ctx.depth >= 1:
        return "error: sub-agents can't spawn their own sub-agents in this demo"
    task = arguments.get("task", "")
    child_key = ctx.gateway.next_subagent_key()
    return ctx.gateway.handle_message(child_key, task, depth=ctx.depth + 1)


TOOLS = {
    "calculator": calculator,
    "read_file": read_file,
    "write_file": write_file,
    "sessions_spawn": sessions_spawn,
}

TOOL_DESCRIPTIONS = """\
- calculator(expression) — evaluate arithmetic, e.g. "482 * 17 - 96"
- read_file(path) — read a text file from the workspace
- write_file(path, content) — write a text file to the workspace
- sessions_spawn(task) — delegate a task to a fresh sub-agent and get its answer back"""


def parse_tool_call(text: str) -> ToolCall | None:
    """The "Tool calls in reply?" decision diamond. Real OpenClaw gets a
    structured tool_use block straight from the provider's API. This demo's
    system prompt (see context.py) instead asks the model to reply with one
    line of JSON when it wants a tool, so parsing is just: does this look
    like {"tool": ..., "arguments": {...}}?
    """
    stripped = text.strip()
    if not stripped.startswith("{"):
        return None
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or "tool" not in data:
        return None
    return ToolCall(name=data["tool"], arguments=data.get("arguments") or {})


def run_tool(call: ToolCall, ctx: ToolContext) -> str:
    fn = TOOLS.get(call.name)
    if fn is None:
        return f"error: unknown tool {call.name!r}"
    return fn(call.arguments, ctx)
