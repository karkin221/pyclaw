"""
AgentLoop — "the agent loop" box on the diagram: one serialized run that
turns a message into actions and a reply (docs/concepts/agent-loop.md calls
this out almost verbatim). Mirrors runEmbeddedAgent in
src/agents/embedded-agent-runner/, minus per-session queueing, token
streaming, plugin hooks, and auto-compaction.
"""
import json

from .context import ContextEngine
from .tools import ToolContext, parse_tool_calls, run_tool
from .trace import stage, trace, trace_block, trace_tokens

MAX_TOOL_HOPS = 4  # safety valve against an infinite tool-call loop — the
# default every demo here uses. Bounds model round-trips, not individual
# tool calls, since one turn can now carry several (see parse_tool_calls).
# Override via max_tool_hops= (AgentLoop or Gateway) for tasks that
# legitimately need more hops; see run_task.py.
NO_REPLY = "NO_REPLY"  # same silent-token convention real OpenClaw uses


class AgentLoop:
    def __init__(
        self, session, workspace, model, gateway, depth: int = 0, max_tool_hops: int = MAX_TOOL_HOPS
    ):
        self.session = session
        self.workspace = workspace
        self.model = model
        self.gateway = gateway
        self.depth = depth
        self.max_tool_hops = max_tool_hops
        self.context_engine = ContextEngine()

    def run(self, user_text: str) -> str:
        self.session.history.append({"role": "user", "content": user_text})

        for _hop in range(self.max_tool_hops):
            stage("① Context assembly")
            messages = self.context_engine.assemble(self.session, self.workspace)

            stage("② Model inference")
            turn = self.model.infer(messages)
            trace_tokens(turn)
            if turn.thinking:
                trace_block("thinking", turn.thinking)

            calls = parse_tool_calls(turn.text)

            if not calls:
                stage("④ Reply shaping")
                reply = turn.text.strip()
                self.session.history.append({"role": "assistant", "content": reply})
                if reply != NO_REPLY:
                    self.workspace.write_episodic_note(self.session.session_key, user_text, reply)
                return "" if reply == NO_REPLY else reply

            # One or more tool calls from this single turn: record the raw
            # turn once, run every call in order, then feed all results back
            # as one combined turn before looping. Real OpenClaw's runner
            # collects however many tool_use blocks came back on one turn
            # the same way (clientToolCalls/pendingToolCalls) instead of
            # forcing a model round-trip per call — see tools.parse_tool_calls.
            self.session.history.append({"role": "assistant", "content": turn.text})
            if len(calls) > 1:
                trace(
                    "batch",
                    f"{len(calls)} tool calls this turn — " + ", ".join(c.name for c in calls),
                )

            ctx = ToolContext(workspace=self.workspace, gateway=self.gateway, depth=self.depth)
            result_lines = []
            for call in calls:
                stage("③ Tool execution", call.name)
                trace_block("arguments", json.dumps(call.arguments, indent=2))
                result = run_tool(call, ctx)
                trace_block("result", result)
                result_lines.append(f"[tool result for {call.name}] {result}")

            # Folded into one labelled user turn (rather than a dedicated
            # "tool" role, or one history entry per call) so this works with
            # plain chat templates across different small models, not just
            # ones that support a tool-result role.
            self.session.history.append({"role": "user", "content": "\n".join(result_lines)})

        stage("④ Reply shaping (tool-hop limit reached)")
        return f"I couldn't finish that within this demo's tool-call limit ({self.max_tool_hops} turns)."
