from dataclasses import dataclass
from decimal import Decimal

from modelwatch.price_parsing import is_known_price, parse_per_token

PRICING_FIELDS = (
    "prompt",
    "completion",
    "image",
    "request",
    "internal_reasoning",
    "input_cache_read",
    "input_cache_write",
    "web_search",
)


@dataclass(frozen=True)
class PriceDropThresholds:
    min_pct: Decimal
    min_saved_per_million_usd: Decimal


DEFAULT_THRESHOLDS = PriceDropThresholds(
    min_pct=Decimal("0.10"),
    min_saved_per_million_usd=Decimal("0.05"),
)


def per_million_field_name(field: str) -> str:
    return f"{field}_per_million"


def per_million_usd(per_token: str) -> Decimal:
    token = parse_per_token(per_token)
    if token is None or not is_known_price(token):
        raise ValueError(f"not a displayable price: {per_token!r}")
    return token * Decimal(1_000_000)


def pricing_fields_to_compare(
    old_pricing: dict[str, str],
    new_pricing: dict[str, str],
) -> tuple[str, ...]:
    return tuple(
        field
        for field in PRICING_FIELDS
        if field in old_pricing and field in new_pricing
    )
