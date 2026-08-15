"""
MockModelProvider — a fake model with the exact same shape as the real one
(one method, `.infer(messages) -> ModelTurn`), used by sanity_check.py to
exercise the entire system in seconds, with no download and no GPU.

This does NOT import transformers or torch, so it works even before you've
installed either — handy for checking the plumbing first.
"""
from .model import ModelTurn


class MockModelProvider:
    """Plays back a fixed script of turns, one per call to `.infer()`,
    regardless of what the messages actually say. Good enough to drive the
    whole agent loop — including a nested sub-agent call, which consumes
    turns from the same script in call order — deterministically."""

    def __init__(self, script: list[str]):
        self._script = list(script)

    def infer(self, messages: list[dict]) -> ModelTurn:
        if not self._script:
            return ModelTurn(text="(mock model ran out of scripted turns)")
        return ModelTurn(text=self._script.pop(0))
