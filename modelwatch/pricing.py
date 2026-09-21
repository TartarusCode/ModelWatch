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
class PriceChangeThresholds:
    min_pct: Decimal
    min_delta_per_million_usd: Decimal


DEFAULT_THRESHOLDS = PriceChangeThresholds(
    min_pct=Decimal("0.10"),
    min_delta_per_million_usd=Decimal("0.05"),
)

# Scheduled models are tracked on two price tracks per field: the standard rate
# (the rate outside any discount window) and the off-peak rate (the cheapest
# scheduled rate). The off-peak track is what makes a deeper discount visible
# even when the standard rate does not move.
TIER_OFFPEAK = "offpeak"
TIER_LABELS = {TIER_OFFPEAK: "off-peak"}


def track_key(field: str, tier: str | None) -> str:
    """State key for a price track: the plain field name, or ``field_tier``."""
    return field if tier is None else f"{field}_{tier}"


def split_track_key(key: str) -> tuple[str, str | None]:
    for tier in TIER_LABELS:
        suffix = f"_{tier}"
        if key.endswith(suffix):
            return key[: -len(suffix)], tier
    return key, None


def tier_label(tier: str | None) -> str | None:
    if tier is None:
        return None
    return TIER_LABELS.get(tier, tier)


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
