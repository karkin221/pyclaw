"""
openclaw_mini — a stripped-down, runnable reimplementation of OpenClaw's
agentic workflow (see ../README.md for the stage-by-stage walkthrough and
../docs/agentic-workflow.png for the diagram this code follows).

Every module here maps to one box on that diagram. Nothing in this package
talks to the network except openclaw_mini.model, which downloads one small
open-weights model from Hugging Face the first time you run it.
"""
