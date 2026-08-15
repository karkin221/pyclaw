"""
Gateway — the box every message passes through first (routing in) and last
(delivery out) on the diagram. Real OpenClaw's Gateway is a single
long-lived WebSocket daemon juggling 30+ channel adapters, agent bindings,
and per-session/global queue lanes (docs/concepts/architecture.md,
docs/concepts/queue.md). This is a same-process router over a plain dict of
sessions — no channels, no concurrency control, no bindings.
"""
from .agent_loop import AgentLoop
from .session import Session


class Gateway:
    def __init__(self, workspace, model, max_tool_hops: int | None = None):
        self.workspace = workspace
        self.model = model
        self.sessions: dict[str, Session] = {}
        self._subagent_counter = 0
        # None means "let AgentLoop use its own default" (see agent_loop.py).
        # Set this to raise the ceiling for every call this Gateway makes —
        # e.g. an open-ended task script like run_task.py.
        self.max_tool_hops = max_tool_hops

    def handle_message(self, session_key: str, text: str, depth: int = 0) -> str:
        """Every entry surface on the diagram (chat channels, CLI, Web
        Control UI, mobile nodes, automation) collapses to a call to this
        one method in this demo — see main.py."""
        session = self.sessions.setdefault(session_key, Session(session_key))
        loop_kwargs = dict(
            session=session, workspace=self.workspace, model=self.model, gateway=self, depth=depth
        )
        if self.max_tool_hops is not None:
            loop_kwargs["max_tool_hops"] = self.max_tool_hops
        loop = AgentLoop(**loop_kwargs)
        return loop.run(text)

    def next_subagent_key(self) -> str:
        self._subagent_counter += 1
        return f"subagent:{self._subagent_counter}"
