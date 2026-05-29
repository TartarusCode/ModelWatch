from dataclasses import dataclass
from decimal import Decimal

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


@dataclass(frozen=True)
class PriceDrop:
    model_id: str
    field: str
    old_per_million_usd: Decimal
    new_per_million_usd: Decimal
    pct_drop: Decimal
    saved_per_million_usd: Decimal


def per_million_usd(per_token: str) -> Decimal:
    return Decimal(per_token) * Decimal(1_000_000)


def pricing_fields_to_compare(
    old_pricing: dict[str, str],
    new_pricing: dict[str, str],
) -> tuple[str, ...]:
    return tuple(
        field
        for field in PRICING_FIELDS
        if field in old_pricing and field in new_pricing
    )


def _parse_per_token(value: str) -> Decimal | None:
    try:
        return Decimal(value)
    except Exception:
        return None


def detect_price_drops(
    model_id: str,
    old_pricing: dict[str, str],
    new_pricing: dict[str, str],
    thresholds: PriceDropThresholds,
) -> list[PriceDrop]:
    drops: list[PriceDrop] = []
    for field in pricing_fields_to_compare(old_pricing, new_pricing):
        old_token = _parse_per_token(old_pricing[field])
        new_token = _parse_per_token(new_pricing[field])
        if old_token is None or new_token is None:
            continue
        if old_token <= 0:
            continue
        if new_token >= old_token:
            continue
        old_per_million = old_token * Decimal(1_000_000)
        new_per_million = new_token * Decimal(1_000_000)
        saved = old_per_million - new_per_million
        pct_drop = saved / old_per_million
        if pct_drop < thresholds.min_pct:
            continue
        if saved < thresholds.min_saved_per_million_usd:
            continue
        drops.append(
            PriceDrop(
                model_id=model_id,
                field=field,
                old_per_million_usd=old_per_million,
                new_per_million_usd=new_per_million,
                pct_drop=pct_drop,
                saved_per_million_usd=saved,
            )
        )
    return drops
