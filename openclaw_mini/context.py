"""
ContextEngine — diagram stage "① Context assembly".

The name and the method, `assemble()`, are taken straight from
docs/concepts/context-engine.md: a context engine's job is to turn a
session's history plus the workspace files into the exact list of messages
the model sees. Real OpenClaw's engine also enforces a token budget and
calls out to `compact()` when history gets too long, and is itself
pluggable (docs/concepts/context-engine.md lists a `legacy` engine plus
installable alternatives). This is the "legacy" shape with the budgeting and
pluggability stripped out — it always includes the full session history.
"""

from .tools import TOOL_DESCRIPTIONS

SYSTEM_TEMPLATE = """\
{agents}

# Persona
{soul}

# About the user
{user}

# Long-term memory
{memory}

# Tools
You can use these tools when they help:
{tools}

To call one tool, reply with EXACTLY one line of JSON and nothing else:
{{"tool": "<name>", "arguments": {{...}}}}
To call more than one tool at once, reply with a JSON array of that same
shape instead:
[{{"tool": "<name>", "arguments": {{...}}}}, {{"tool": "<name>", "arguments": {{...}}}}]
Otherwise just answer normally in plain text — short and direct.
"""


class ContextEngine:
    def assemble(self, session, workspace) -> list[dict]:
        files = workspace.read_bootstrap_files()
        system_prompt = SYSTEM_TEMPLATE.format(
            agents=files["AGENTS.md"] or "(no AGENTS.md yet)",
            soul=files["SOUL.md"] or "(no SOUL.md yet)",
            user=files["USER.md"] or "(no USER.md yet)",
            memory=files["MEMORY.md"] or "(nothing remembered yet)",
            tools=TOOL_DESCRIPTIONS,
        )
        return [{"role": "system", "content": system_prompt}] + session.history
