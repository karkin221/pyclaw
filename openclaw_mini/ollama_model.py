"""
Alternate model layer — same diagram stage "② Model inference" as
model.py, but talking to a locally running Ollama server over plain HTTP
instead of loading Hugging Face weights in-process. Real OpenClaw's
provider layer includes an Ollama provider alongside its hosted ones
(src/llm/providers/, docs/concepts/agent-loop.md); this is the minimal
stand-in for that one.

Picked as a second backend because `ollama serve` needs no torch/
transformers install and no Hugging Face download — just a running Ollama
server and a pulled model. Uses only the standard library (urllib), so
this module works even without `pip install -r requirements.txt`.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .model import ModelTurn

# Mirrors model.py's DEFAULT_MODEL choice — small, instruction-tuned, and
# reasonable at following this demo's "reply with JSON to call a tool"
# instruction. Any small instruction-tuned tag from `ollama pull` works;
# swap it for a bigger sibling (qwen3:8b, qwen3:14b, ...) for more
# reliable tool calls, same trade-off as model.py's DEFAULT_MODEL comment.
DEFAULT_OLLAMA_MODEL = "qwen3:4b"

DEFAULT_HOST = "http://localhost:11434"


class OllamaModelProvider:
    """Same one-method shape every provider in this demo exposes:
    `.infer(messages) -> ModelTurn`. Talks to POST /api/chat on a local
    Ollama server (API shape: https://github.com/ollama/ollama/blob/main/docs/api.md).

    Swappable by design, like ModelProvider and MockModelProvider — the
    rest of the codebase (context.py, agent_loop.py, memory.py, ...) never
    needs to know which one it's talking to.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_OLLAMA_MODEL,
        host: str = DEFAULT_HOST,
        timeout: float = 300.0,
    ):
        self.model_name = model_name
        self.host = host.rstrip("/")
        self.timeout = timeout
        self._check_reachable()

    def _check_reachable(self) -> None:
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=5):
                pass
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ConnectionError(
                f"can't reach an Ollama server at {self.host} — is `ollama serve` "
                f"running there? ({exc})"
            ) from exc

    def infer(self, messages: list[dict]) -> ModelTurn:
        payload = json.dumps(
            {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
                # Hybrid-thinking models (Qwen3 and others) default to emitting
                # a <think>...</think> reasoning block before the answer. That
                # both slows generation a lot and would break
                # tools.parse_tool_call's plain "does this start with {"
                # check, so it's turned off explicitly. Ollama ignores this
                # option on models that don't support it.
                "think": False,
            }
        ).encode()
        request = urllib.request.Request(
            f"{self.host}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                body = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise RuntimeError(
                f"Ollama returned HTTP {exc.code} for model {self.model_name!r} — "
                f"pulled yet? Try `ollama pull {self.model_name}`. Detail: {detail}"
            ) from exc
        except TimeoutError as exc:
            raise TimeoutError(
                f"Ollama took longer than {self.timeout:.0f}s to reply for model "
                f"{self.model_name!r} — small models can be slow on CPU-only "
                f"hardware. Pass a bigger timeout= to OllamaModelProvider if this "
                f"keeps happening, e.g. OllamaModelProvider(timeout=600)."
            ) from exc
        text = body.get("message", {}).get("content", "")
        return ModelTurn(text=text.strip())
