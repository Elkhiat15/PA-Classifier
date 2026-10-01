"""Runtime metrics for classifier calls: latency, tokens, and estimated cost.

Latency is wall-clock time around the model call. Token usage is captured from
the LangChain callback system (``on_llm_end``), which exposes provider usage in
several shapes depending on the integration. Cost is a best-effort estimate
computed from a small pricing table (USD per 1M tokens), overridable per
provider via the ``PA_PRICE_<PROVIDER>`` env var as ``"input,output"``.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

# USD per 1,000,000 tokens: provider -> (input_price, output_price).
#   gemini  -> gemini-2.5-flash
#   mistral -> ministral-8b-2512
#   groq    -> qwen/qwen3.8-27b
# Treat the resulting cost as an estimate, not billing.
DEFAULT_PRICING: dict[str, tuple[float, float]] = {
    # From Openrouter
    "gemini": (0.10, 0.40),
    "mistral": (0.15, 0.15),
    "groq": (0.0248, 4.35),
}


def _pricing_for(provider: str) -> tuple[float, float]:
    """Return (input, output) USD/1M-token prices for ``provider``."""
    override = os.environ.get(f"PA_PRICE_{provider.upper()}")
    if override:
        try:
            inp_str, out_str = override.split(",")
            return float(inp_str), float(out_str)
        except ValueError:
            pass
    return DEFAULT_PRICING.get(provider, (0.0, 0.0))


@dataclass
class CallMetrics:
    """Metrics collected for a single model call."""

    provider: str
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "latency_ms": round(self.latency_ms, 1),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
        }


def _extract_usage(response: Any) -> tuple[int, int]:
    """Best-effort (prompt_tokens, completion_tokens) from an ``LLMResult``."""
    # 1) LangChain standard: AIMessage.usage_metadata.
    try:
        message = response.generations[0][0].message
        usage = getattr(message, "usage_metadata", None)
        if usage:
            prompt = usage.get("input_tokens", 0) or 0
            completion = usage.get("output_tokens", 0) or 0
            if prompt or completion:
                return int(prompt), int(completion)
    except (IndexError, AttributeError, TypeError):
        pass

    # 2) Provider-level "llm_output" (OpenAI-compatible token_usage / usage).
    llm_output = getattr(response, "llm_output", None) or {}
    usage = llm_output.get("token_usage") or llm_output.get("usage") or {}
    if usage:
        prompt = usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0
        completion = usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0
        if prompt or completion:
            return int(prompt), int(completion)

    # 3) Provider-specific generation_info (Groq / Mistral style).
    for gen_list in getattr(response, "generations", []) or []:
        for gen in gen_list:
            info = getattr(gen, "generation_info", None) or {}
            usage = info.get("usage") or info.get("token_usage") or {}
            if usage:
                prompt = usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0
                completion = usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0
                if prompt or completion:
                    return int(prompt), int(completion)

    return 0, 0


class MetricsCallbackHandler(BaseCallbackHandler):
    """Collect token usage emitted when a model call finishes."""

    raise_on_error = False

    def __init__(self) -> None:
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        prompt, completion = _extract_usage(response)
        if prompt or completion:
            self.prompt_tokens = prompt
            self.completion_tokens = completion


def measure(provider: str, fn, *args, **kwargs):
    """Run ``fn`` (a model ``.invoke``) and return ``(result, CallMetrics)``.

    A metrics callback is attached through the LangChain config so token usage
    is captured without touching the provider clients. Latency is wall-clock
    around the call.
    """
    handler = MetricsCallbackHandler()

    config = dict(kwargs.pop("config", None) or {})
    callbacks = list(config.get("callbacks") or [])
    callbacks.append(handler)
    config["callbacks"] = callbacks

    start = time.perf_counter()
    result = fn(*args, config=config, **kwargs)
    latency_ms = (time.perf_counter() - start) * 1000.0

    prompt_tokens = handler.prompt_tokens
    completion_tokens = handler.completion_tokens
    total_tokens = prompt_tokens + completion_tokens

    in_price, out_price = _pricing_for(provider)
    cost = (prompt_tokens / 1_000_000) * in_price + (
        completion_tokens / 1_000_000
    ) * out_price

    metrics = CallMetrics(
        provider=provider,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=cost,
    )
    return result, metrics