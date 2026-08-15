"""
AgentLoop — "the agent loop" box on the diagram: one serialized run that
turns a message into actions and a reply (docs/concepts/agent-loop.md calls
this out almost verbatim). Mirrors runEmbeddedAgent in
src/agents/embedded-agent-runner/, minus per-session queueing, token
streaming, plugin hooks, and auto-compaction.
"""
from .context import ContextEngine
from .tools import ToolContext, parse_tool_call, run_tool

MAX_TOOL_HOPS = 4  # safety valve against an infinite tool-call loop — the
# default every demo here uses. Override via max_tool_hops= (AgentLoop or
# Gateway) for tasks that legitimately need more hops; see run_task.py.
NO_REPLY = "NO_REPLY"  # same silent-token convention real OpenClaw uses


def stage(label: str, detail: str = "") -> None:
    """Console narration only. Every call marks entering one box on the
    diagram, in order, so `python main.py` reads like the diagram lighting
    up one stage at a time."""
    print(f"    · {label}" + (f" — {detail}" if detail else ""))


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

            call = parse_tool_call(turn.text)

            if call is None:
                stage("④ Reply shaping")
                reply = turn.text.strip()
                self.session.history.append({"role": "assistant", "content": reply})
                if reply != NO_REPLY:
                    self.workspace.write_episodic_note(self.session.session_key, user_text, reply)
                return "" if reply == NO_REPLY else reply

            # A tool call: record it, run it, feed the result back in, loop.
            self.session.history.append({"role": "assistant", "content": turn.text})
            stage("③ Tool execution", call.name)
            ctx = ToolContext(workspace=self.workspace, gateway=self.gateway, depth=self.depth)
            result = run_tool(call, ctx)
            # Folded into a labelled user turn (rather than a dedicated "tool"
            # role) so this works with plain chat templates across different
            # small models, not just ones that support a tool-result role.
            self.session.history.append(
                {"role": "user", "content": f"[tool result for {call.name}] {result}"}
            )

        stage("④ Reply shaping (tool-hop limit reached)")
        return f"I couldn't finish that within this demo's tool-call limit ({self.max_tool_hops} hops)."
