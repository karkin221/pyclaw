"""
Model layer — diagram stage "② Model inference".

Real OpenClaw talks to hosted providers (Anthropic, OpenAI, local models,
and more — src/llm/providers/) with streaming, retries, and failover
(docs/concepts/agent-loop.md, docs/concepts/model-failover.md). This demo
talks to one small open-weights model running locally through Hugging Face
`transformers`, greedily and synchronously, so the whole loop runs with no
API keys and no cloud calls once the weights are on disk.

transformers/torch are imported lazily inside ModelProvider.__init__, not at
module level, so the rest of this package (and openclaw_mini.mock_model) can
be imported and unit-tested without either installed.
"""
from dataclasses import dataclass

# Small, instruction-tuned, and — importantly for this demo — trained to
# follow a plain-text "reply with JSON to call a tool" instruction reasonably
# well. Swap this for a bigger sibling (Qwen2.5-3B-Instruct, 7B, ...) for
# more reliable tool calls, or a smaller one for a faster/lighter download.
DEFAULT_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"


@dataclass
class ModelTurn:
    """One raw turn out of the model, before the agent loop decides whether
    it's a tool call or a reply. Real OpenClaw's provider layer returns a
    richer structured turn (text + native tool_use blocks + usage); this is
    the minimal version — text plus, when the provider reports them,
    reasoning/thinking and token counts — since tool calls here are parsed
    out of plain text (see openclaw_mini.tools.parse_tool_calls).

    thinking/input_tokens/output_tokens are all optional and default to
    None: MockModelProvider never sets them, ModelProvider (below) always
    can, and OllamaModelProvider can when the server reports them."""

    text: str
    thinking: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


def split_thinking(text: str) -> tuple[str, str | None]:
    """Split a raw completion into (answer, thinking) when it contains a
    hybrid-thinking reasoning block (Qwen3 and others). The real answer is
    everything after the LAST </think> — some providers prime the opening
    <think> tag into the prompt template rather than generating it, so only
    the closing tag may actually show up in the text — and this returns
    (text, None) unchanged when there's no thinking block at all."""
    if "</think>" not in text:
        return text.strip(), None
    thinking, _, answer = text.rpartition("</think>")
    thinking = thinking.removeprefix("<think>").strip()
    return answer.strip(), (thinking or None)


class ModelProvider:
    """Wraps one local Hugging Face causal LM behind the same shape every
    provider in real OpenClaw exposes: hand it `messages`, get back a turn.

    Swappable by design — openclaw_mini.mock_model.MockModelProvider has the
    exact same one method, `.infer(messages) -> ModelTurn`, so the rest of
    the codebase never needs to know which one it's talking to.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL, max_new_tokens: int = 400):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch

        self._torch = torch
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens

        print(f"  loading {model_name} (first run downloads the weights, ~1-3GB)...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype="auto")
        print("  model ready.\n")

    def infer(self, messages: list[dict]) -> ModelTurn:
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer(prompt, return_tensors="pt")

        with self._torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,  # greedy — deterministic and simple, no sampling knobs to tune
                pad_token_id=self.tokenizer.eos_token_id,
            )

        generated = output_ids[0][inputs["input_ids"].shape[1]:]
        raw_text = self.tokenizer.decode(generated, skip_special_tokens=True)
        text, thinking = split_thinking(raw_text)
        return ModelTurn(
            text=text,
            thinking=thinking,
            input_tokens=int(inputs["input_ids"].shape[1]),
            output_tokens=int(generated.shape[0]),
        )
