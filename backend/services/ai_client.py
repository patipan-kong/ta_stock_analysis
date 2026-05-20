"""
Unified AI client — single call_ai() works across all providers.
- anthropic: uses anthropic SDK
- all others (openai, deepseek, zhipu, groq, gemini): OpenAI-compatible SDK with custom base_url

call_ai() returns a dict: {"text": str, "latency_ms": int, "input_tokens": int,
                            "output_tokens": int, "provider": str, "model": str}
"""

import os
import json
import time
from functools import lru_cache
from dotenv import load_dotenv
from models.database import SessionLocal, UserUsage

load_dotenv()

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai-model.json")


@lru_cache(maxsize=1)
def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _find_model_pricing(config: dict, model: str) -> tuple[float, float]:
    for m in config.get("models", []):
        if m.get("id") == model or m.get("apiModel") == model:
            token_1m = (m.get("cost") or {}).get("token_1m") or {}
            return float(token_1m.get("input", 0.0) or 0.0), float(token_1m.get("output", 0.0) or 0.0)
    return 0.0, 0.0


def _compute_cost_usd(input_tokens: int, output_tokens: int, in_per_1m: float, out_per_1m: float) -> tuple[float, float, float]:
    input_cost = (input_tokens / 1_000_000) * in_per_1m
    output_cost = (output_tokens / 1_000_000) * out_per_1m
    return input_cost, output_cost, input_cost + output_cost


def _record_usage(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    input_cost_usd: float,
    output_cost_usd: float,
    total_cost_usd: float,
    operation: str,
    layer: str | None,
    latency_ms: int = 0,
) -> None:
    db = SessionLocal()
    try:
        db.add(UserUsage(
            provider=provider,
            model=model,
            operation=operation,
            layer=layer,
            input_tokens=max(0, int(input_tokens)),
            output_tokens=max(0, int(output_tokens)),
            total_tokens=max(0, int(input_tokens) + int(output_tokens)),
            input_cost_usd=float(input_cost_usd),
            output_cost_usd=float(output_cost_usd),
            total_cost_usd=float(total_cost_usd),
            latency_ms=int(latency_ms),
        ))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def call_ai(
    prompt: str,
    provider: str,
    model: str,
    max_tokens: int = 4096,
    usage_operation: str = "other",
    usage_layer: str | None = None,
) -> dict:
    """
    Send a prompt to any supported AI provider.
    Returns dict: {"text": str, "latency_ms": int, "input_tokens": int,
                   "output_tokens": int, "provider": str, "model": str}
    JSON parsing (safe_parse_json) should be done by the caller, not here.
    """
    config = _load_config()
    provider_config = config.get("providers", {}).get(provider, {})
    api_key = os.getenv(provider_config.get("envKey", ""), "") or "dummy"
    base_url: str = provider_config.get("baseURL", "")
    in_per_1m, out_per_1m = _find_model_pricing(config, model)

    if provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        start = time.perf_counter()
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        latency_ms = round((time.perf_counter() - start) * 1000)
        usage = getattr(message, "usage", None)
        in_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        out_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        in_cost, out_cost, total_cost = _compute_cost_usd(in_tokens, out_tokens, in_per_1m, out_per_1m)
        _record_usage(provider, model, in_tokens, out_tokens, in_cost, out_cost, total_cost, usage_operation, usage_layer, latency_ms)
        return {
            "text": message.content[0].text,
            "latency_ms": latency_ms,
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "provider": provider,
            "model": model,
        }

    # All other providers: OpenAI-compatible interface
    # gpt-5, o1, o3, o4 and future reasoning models use max_completion_tokens instead of max_tokens
    _REASONING_PATTERNS = ("gpt-5", "o1", "o3", "o4")
    _uses_completion_tokens = (
        provider in ("openai", "deepseek", "zhipu")
        and any(pat in model for pat in _REASONING_PATTERNS)
    )

    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url or None)
    create_kwargs: dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if _uses_completion_tokens:
        create_kwargs["max_completion_tokens"] = max_tokens
    else:
        create_kwargs["max_tokens"] = max_tokens

    start = time.perf_counter()
    response = client.chat.completions.create(**create_kwargs)
    latency_ms = round((time.perf_counter() - start) * 1000)

    usage = getattr(response, "usage", None)
    in_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    out_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    in_cost, out_cost, total_cost = _compute_cost_usd(in_tokens, out_tokens, in_per_1m, out_per_1m)
    _record_usage(provider, model, in_tokens, out_tokens, in_cost, out_cost, total_cost, usage_operation, usage_layer, latency_ms)

    msg = response.choices[0].message
    content = msg.content or ""

    # Reasoning models (DeepSeek-R1, GLM-Z1) keep chain-of-thought in
    # reasoning_content and the final answer in content. If content is empty
    # the model may have embedded its answer inside the thinking block —
    # combine both so safe_parse_json can find the JSON object wherever it is.
    if not content:
        extra = getattr(msg, "model_extra", {}) or {}
        content = extra.get("reasoning_content") or ""

    return {
        "text": content,
        "latency_ms": latency_ms,
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "provider": provider,
        "model": model,
    }
