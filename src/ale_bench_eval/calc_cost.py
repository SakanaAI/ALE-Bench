from decimal import Decimal

from genai_prices import Usage, calc_price
from genai_prices.types import ModelPrice, Tier, TieredPrices
from pydantic_ai.usage import RunUsage

FALLBACK_DICT = {
    "gpt-5.4-nano-2026-03-17": ModelPrice(
        input_mtok=Decimal(2) / Decimal(10),
        cache_read_mtok=Decimal(2) / Decimal(100),
        output_mtok=Decimal(125) / Decimal(100),
    ),
    "gpt-5.4-mini-2026-03-17": ModelPrice(
        input_mtok=Decimal(75) / Decimal(100),
        cache_read_mtok=Decimal(75) / Decimal(1000),
        output_mtok=Decimal(45) / Decimal(10),
    ),
    "gpt-5.4-2026-03-05": ModelPrice(
        input_mtok=Decimal(25) / Decimal(10),
        cache_read_mtok=Decimal(25) / Decimal(100),
        output_mtok=Decimal(15),
    ),
    "gpt-5.3-codex": ModelPrice(
        input_mtok=Decimal(175) / Decimal(100),
        cache_read_mtok=Decimal(175) / Decimal(1000),
        output_mtok=Decimal(14),
    ),
    "gpt-5.2-2025-12-11": ModelPrice(
        input_mtok=Decimal(175) / Decimal(100),
        cache_read_mtok=Decimal(175) / Decimal(1000),
        output_mtok=Decimal(14),
    ),
    "gpt-5.2-codex": ModelPrice(
        input_mtok=Decimal(175) / Decimal(100),
        cache_read_mtok=Decimal(175) / Decimal(1000),
        output_mtok=Decimal(14),
    ),
    "gpt-5.1-codex-max": ModelPrice(
        input_mtok=Decimal(125) / Decimal(100),
        cache_read_mtok=Decimal(125) / Decimal(1000),
        output_mtok=Decimal(10),
    ),
    "gemini-3-flash-preview": ModelPrice(
        input_mtok=Decimal(5) / Decimal(10),
        cache_read_mtok=Decimal(5) / Decimal(100),
        output_mtok=Decimal(3),
    ),
    "gemini-3.1-pro-preview": ModelPrice(
        input_mtok=TieredPrices(base=Decimal(2), tiers=[Tier(start=200000, price=Decimal(4))]),
        output_mtok=TieredPrices(base=Decimal(12), tiers=[Tier(start=200000, price=Decimal(18))]),
        cache_read_mtok=TieredPrices(
            base=Decimal(2) / Decimal(10), tiers=[Tier(start=200000, price=Decimal(4) / Decimal(10))]
        ),
        cache_write_mtok=Decimal(375) / Decimal(1000),
    ),
    "gemini-3.1-flash-lite-preview": ModelPrice(
        input_mtok=Decimal(25) / Decimal(100),
        cache_read_mtok=Decimal(25) / Decimal(1000),
        output_mtok=Decimal(15) / Decimal(10),
    ),
    "gemma-4-26b-a4b-it": ModelPrice(input_mtok=Decimal(13) / Decimal(100), output_mtok=Decimal(4) / Decimal(10)),
    "claude-sonnet-4": ModelPrice(
        input_mtok=TieredPrices(base=Decimal(3), tiers=[Tier(start=200000, price=Decimal(6))]),
        cache_write_mtok=TieredPrices(
            base=Decimal(375) / Decimal(100), tiers=[Tier(start=200000, price=Decimal(75) / Decimal(10))]
        ),
        cache_read_mtok=TieredPrices(
            base=Decimal(3) / Decimal(10), tiers=[Tier(start=200000, price=Decimal(6) / Decimal(10))]
        ),
        output_mtok=TieredPrices(base=Decimal(15), tiers=[Tier(start=200000, price=Decimal(225) / Decimal(10))]),
    ),
    "claude-opus-4.1": ModelPrice(
        input_mtok=Decimal(15),
        cache_write_mtok=Decimal(1875) / Decimal(100),
        cache_read_mtok=Decimal(15) / Decimal(10),
        output_mtok=Decimal(75),
    ),
    "claude-sonnet-4.5": ModelPrice(
        input_mtok=TieredPrices(base=Decimal(3), tiers=[Tier(start=200000, price=Decimal(6))]),
        cache_write_mtok=TieredPrices(
            base=Decimal(375) / Decimal(100), tiers=[Tier(start=200000, price=Decimal(75) / Decimal(10))]
        ),
        cache_read_mtok=TieredPrices(
            base=Decimal(3) / Decimal(10), tiers=[Tier(start=200000, price=Decimal(6) / Decimal(10))]
        ),
        output_mtok=TieredPrices(base=Decimal(15), tiers=[Tier(start=200000, price=Decimal(225) / Decimal(10))]),
    ),
    "claude-haiku-4.5": ModelPrice(
        input_mtok=Decimal(1),
        cache_write_mtok=Decimal(125) / Decimal(100),
        cache_read_mtok=Decimal(1) / Decimal(10),
        output_mtok=Decimal(5),
    ),
    "claude-opus-4.5": ModelPrice(
        input_mtok=Decimal(5),
        cache_write_mtok=Decimal(625) / Decimal(100),
        cache_read_mtok=Decimal(5) / Decimal(10),
        output_mtok=Decimal(25),
    ),
    "claude-opus-4.6": ModelPrice(
        input_mtok=Decimal(5),
        cache_write_mtok=Decimal(625) / Decimal(100),
        cache_read_mtok=Decimal(5) / Decimal(10),
        output_mtok=Decimal(25),
    ),
    "claude-sonnet-4.6": ModelPrice(
        input_mtok=Decimal(3),
        cache_write_mtok=Decimal(375) / Decimal(100),
        cache_read_mtok=Decimal(3) / Decimal(10),
        output_mtok=Decimal(15),
    ),
    "grok-4.1-fast": ModelPrice(
        input_mtok=Decimal(2) / Decimal(10),
        cache_read_mtok=Decimal(5) / Decimal(100),
        output_mtok=Decimal(5) / Decimal(10),
    ),
    "grok-4.20-beta": ModelPrice(
        input_mtok=TieredPrices(base=Decimal(2), tiers=[Tier(start=200000, price=Decimal(4))]),
        cache_read_mtok=Decimal(2) / Decimal(10),
        output_mtok=TieredPrices(base=Decimal(6), tiers=[Tier(start=200000, price=Decimal(12))]),
    ),
    "nova-premier-v1": ModelPrice(
        input_mtok=Decimal(25) / Decimal(10),
        cache_read_mtok=Decimal(625) / Decimal(1000),
        output_mtok=Decimal(125) / Decimal(10),
    ),
    "nova-2-lite-v1": ModelPrice(input_mtok=Decimal(3) / Decimal(10), output_mtok=Decimal(25) / Decimal(10)),
    "deepseek-v3.1": ModelPrice(input_mtok=Decimal(56) / Decimal(100), output_mtok=Decimal(168) / Decimal(100)),
    "deepseek-v3.1-terminus": ModelPrice(input_mtok=Decimal(27) / Decimal(100), output_mtok=Decimal(1)),
    "deepseek-v3.2": ModelPrice(input_mtok=Decimal(27) / Decimal(100), output_mtok=Decimal(42) / Decimal(10)),
    "deepseek-r1-0528": ModelPrice(input_mtok=Decimal(79) / Decimal(100), output_mtok=Decimal(4)),
    "mimo-v2-flash:free": ModelPrice(input_mtok=Decimal(1) / Decimal(10), output_mtok=Decimal(3) / Decimal(10)),
    "mimo-v2-pro": ModelPrice(
        input_mtok=TieredPrices(
            base=Decimal(1),
            tiers=[Tier(start=256000, price=Decimal(2))],
        ),
        output_mtok=TieredPrices(
            base=Decimal(3),
            tiers=[Tier(start=256000, price=Decimal(6))],
        ),
        cache_read_mtok=TieredPrices(
            base=Decimal(2) / Decimal(10),
            tiers=[Tier(start=256000, price=Decimal(4) / Decimal(10))],
        ),
    ),
    "glm-4.5": ModelPrice(input_mtok=Decimal(59) / Decimal(100), output_mtok=Decimal(21) / Decimal(10)),
    "glm-4.6": ModelPrice(
        input_mtok=Decimal(6) / Decimal(10),
        output_mtok=Decimal(22) / Decimal(10),
        cache_read_mtok=Decimal(11) / Decimal(100),
    ),
    "glm-4.7": ModelPrice(
        input_mtok=Decimal(6) / Decimal(10),
        output_mtok=Decimal(22) / Decimal(10),
        cache_read_mtok=Decimal(11) / Decimal(100),
    ),
    "glm-5": ModelPrice(
        input_mtok=Decimal(1),
        output_mtok=Decimal(32) / Decimal(10),
        cache_read_mtok=Decimal(2) / Decimal(10),
    ),
    "glm-5.1": ModelPrice(
        input_mtok=Decimal(14) / Decimal(10),
        output_mtok=Decimal(44) / Decimal(10),
        cache_read_mtok=Decimal(26) / Decimal(100),
    ),
    "glm-5-turbo": ModelPrice(
        input_mtok=Decimal(12) / Decimal(10),
        output_mtok=Decimal(4),
        cache_read_mtok=Decimal(24) / Decimal(100),
    ),
    "gpt-oss-120b": ModelPrice(input_mtok=Decimal(1) / Decimal(10), output_mtok=Decimal(5) / Decimal(10)),
    "gpt-oss-20b": ModelPrice(input_mtok=Decimal(5) / Decimal(100), output_mtok=Decimal(2) / Decimal(10)),
    "grok-code-fast-1": ModelPrice(input_mtok=Decimal(2) / Decimal(10), output_mtok=Decimal(15) / Decimal(10)),
    "llama-4-maverick": ModelPrice(input_mtok=Decimal(18) / Decimal(100), output_mtok=Decimal(6) / Decimal(10)),
    "codestral-2508": ModelPrice(input_mtok=Decimal(3) / Decimal(10), output_mtok=Decimal(9) / Decimal(10)),
    "mistral-medium-3.1": ModelPrice(input_mtok=Decimal(4) / Decimal(10), output_mtok=Decimal(2)),
    "mistral-large-2512": ModelPrice(input_mtok=Decimal(5) / Decimal(10), output_mtok=Decimal(15) / Decimal(10)),
    "mistral-small-2603": ModelPrice(input_mtok=Decimal(15) / Decimal(100), output_mtok=Decimal(6) / Decimal(10)),
    "kimi-k2": ModelPrice(
        input_mtok=Decimal(6) / Decimal(10),
        output_mtok=Decimal(25) / Decimal(10),
        cache_read_mtok=Decimal(15) / Decimal(100),
    ),
    "kimi-k2-0905": ModelPrice(
        input_mtok=Decimal(6) / Decimal(10),
        output_mtok=Decimal(25) / Decimal(10),
        cache_read_mtok=Decimal(15) / Decimal(100),
    ),
    "kimi-k2-thinking": ModelPrice(
        input_mtok=Decimal(6) / Decimal(10),
        output_mtok=Decimal(25) / Decimal(10),
        cache_read_mtok=Decimal(15) / Decimal(100),
    ),
    "kimi-k2.5": ModelPrice(
        input_mtok=Decimal(6) / Decimal(10),
        output_mtok=Decimal(3),
        cache_read_mtok=Decimal(1) / Decimal(10),
    ),
    "minimax-m2.1": ModelPrice(
        input_mtok=Decimal(3) / Decimal(10),
        output_mtok=Decimal(12) / Decimal(10),
        cache_read_mtok=Decimal(3) / Decimal(100),
        cache_write_mtok=Decimal(375) / Decimal(1000),
    ),
    "minimax-m2.5": ModelPrice(
        input_mtok=Decimal(3) / Decimal(10),
        output_mtok=Decimal(12) / Decimal(10),
        cache_read_mtok=Decimal(3) / Decimal(100),
    ),
    "minimax-m2.7": ModelPrice(
        input_mtok=Decimal(3) / Decimal(10),
        output_mtok=Decimal(12) / Decimal(10),
        cache_read_mtok=Decimal(6) / Decimal(100),
    ),
    "nemotron-3-super-120b-a12b:free": ModelPrice(
        input_mtok=Decimal(1) / Decimal(10),
        output_mtok=Decimal(5) / Decimal(10),
        cache_read_mtok=Decimal(1) / Decimal(10),
    ),
    "qwen3-235b-a22b-thinking-2507": ModelPrice(
        input_mtok=Decimal(3) / Decimal(10), output_mtok=Decimal(29) / Decimal(10)
    ),
    "qwen3-coder": ModelPrice(input_mtok=Decimal(29) / Decimal(100), output_mtok=Decimal(12) / Decimal(10)),
    "qwen3-coder-plus": ModelPrice(
        input_mtok=TieredPrices(
            base=Decimal(1),
            tiers=[Tier(start=32000, price=Decimal(18) / Decimal(10))],
        ),
        output_mtok=TieredPrices(
            base=Decimal(5),
            tiers=[Tier(start=32000, price=Decimal(9))],
        ),
        cache_read_mtok=TieredPrices(
            base=Decimal(1) / Decimal(10),
            tiers=[Tier(start=32000, price=Decimal(18) / Decimal(100))],
        ),
    ),
    "qwen3-max": ModelPrice(
        input_mtok=TieredPrices(base=Decimal(12) / Decimal(10), tiers=[Tier(start=128000, price=Decimal(3))]),
        cache_read_mtok=TieredPrices(
            base=Decimal(24) / Decimal(100), tiers=[Tier(start=128000, price=Decimal(6) / Decimal(10))]
        ),
        output_mtok=TieredPrices(base=Decimal(6), tiers=[Tier(start=128000, price=Decimal(15))]),
    ),
    "qwen3-next-80b-a3b-thinking": ModelPrice(
        input_mtok=Decimal(14) / Decimal(100), output_mtok=Decimal(14) / Decimal(10)
    ),
    "qwen3.5-35b-a3b": ModelPrice(input_mtok=Decimal(25) / Decimal(100), output_mtok=Decimal(2)),
    "qwen3.5-397b-a17b": ModelPrice(input_mtok=Decimal(6) / Decimal(10), output_mtok=Decimal(36) / Decimal(10)),
    "qwen3.5-plus-02-15": ModelPrice(
        input_mtok=TieredPrices(
            base=Decimal(4) / Decimal(10), tiers=[Tier(start=256000, price=Decimal(12) / Decimal(10))]
        ),
        output_mtok=TieredPrices(
            base=Decimal(24) / Decimal(10), tiers=[Tier(start=256000, price=Decimal(72) / Decimal(10))]
        ),
    ),
    "qwen3.5-flash-02-23": ModelPrice(input_mtok=Decimal(1) / Decimal(10), output_mtok=Decimal(4) / Decimal(10)),
    "qwen3.6-plus": ModelPrice(
        input_mtok=TieredPrices(base=Decimal(5) / Decimal(10), tiers=[Tier(start=256000, price=Decimal(2))]),
        output_mtok=TieredPrices(base=Decimal(3), tiers=[Tier(start=256000, price=Decimal(6))]),
    ),
}


def calc_cost(usage: Usage | RunUsage, model_name: str) -> float:
    usage_for_price = (
        usage
        if isinstance(usage, Usage)
        else Usage(
            input_tokens=usage.input_tokens,
            cache_write_tokens=usage.cache_write_tokens,
            cache_read_tokens=usage.cache_read_tokens,
            output_tokens=usage.output_tokens,
            input_audio_tokens=usage.input_audio_tokens,
            cache_audio_read_tokens=usage.cache_audio_read_tokens,
            output_audio_tokens=usage.output_audio_tokens,
        )
    )
    model_name = model_name.rsplit("/", maxsplit=1)[-1]  # Use the model name without the provider prefix
    if model_name in FALLBACK_DICT:
        model_price = FALLBACK_DICT[model_name]
        return float(model_price.calc_price(usage_for_price)["total_price"])

    try:
        total_price = float(calc_price(usage_for_price, model_ref=model_name).total_price)
    except LookupError as e:
        msg = f"Model price not found for {model_name}"
        raise LookupError(msg) from e
    if total_price > 0.0:
        return total_price
    msg = "Something wrong with the retrieved price. Calculated price is zero."
    raise LookupError(msg)
