from decimal import Decimal

from genai_prices import Usage, calc_price
from genai_prices.types import ModelPrice, Tier, TieredPrices

FALLBACK_DICT = {
    "gpt-5.1-codex-max": ModelPrice(
        input_mtok=Decimal(125) / Decimal(100),
        cache_read_mtok=Decimal(125) / Decimal(1000),
        output_mtok=Decimal(10),
    ),
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
    "grok-4.1-fast": ModelPrice(
        input_mtok=Decimal(2) / Decimal(10),
        cache_read_mtok=Decimal(5) / Decimal(100),
        output_mtok=Decimal(5) / Decimal(10),
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
    "glm-4.5": ModelPrice(input_mtok=Decimal(59) / Decimal(100), output_mtok=Decimal(21) / Decimal(10)),
    "glm-4.6": ModelPrice(
        input_mtok=Decimal(6) / Decimal(10),
        output_mtok=Decimal(22) / Decimal(10),
        cache_read_mtok=Decimal(11) / Decimal(100),
    ),
    "gpt-oss-120b": ModelPrice(input_mtok=Decimal(1) / Decimal(10), output_mtok=Decimal(5) / Decimal(10)),
    "gpt-oss-20b": ModelPrice(input_mtok=Decimal(5) / Decimal(100), output_mtok=Decimal(2) / Decimal(10)),
    "grok-code-fast-1": ModelPrice(input_mtok=Decimal(2) / Decimal(10), output_mtok=Decimal(15) / Decimal(10)),
    "llama-4-maverick": ModelPrice(input_mtok=Decimal(18) / Decimal(100), output_mtok=Decimal(6) / Decimal(10)),
    "codestral-2508": ModelPrice(input_mtok=Decimal(3) / Decimal(10), output_mtok=Decimal(9) / Decimal(10)),
    "mistral-medium-3.1": ModelPrice(input_mtok=Decimal(4) / Decimal(10), output_mtok=Decimal(2)),
    "mistral-large-2512": ModelPrice(input_mtok=Decimal(5) / Decimal(10), output_mtok=Decimal(15) / Decimal(10)),
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
}


def calc_cost(usage: Usage, model_name: str) -> float:
    model_name = model_name.rsplit("/")[-1]  # Use the model name without the provider prefix
    if model_name in FALLBACK_DICT:
        model_price = FALLBACK_DICT[model_name]
        return float(model_price.calc_price(usage)["total_price"])

    try:
        total_price = float(calc_price(usage, model_ref=model_name).total_price)
        if total_price > 0.0:
            return total_price
        raise LookupError("Something wrong with the retrieved price. Calculated price is zero.")
    except LookupError:
        raise LookupError(f"Model price not found for {model_name}")
