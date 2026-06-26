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
    token = _parse_per_token(per_token)
    if token is None or not _is_known_price(token):
        raise ValueError(f"not a displayable price: {per_token!r}")
    return token * Decimal(1_000_000)


def _is_known_price(token: Decimal) -> bool:
    return token >= 0


def _is_positive_price(token: Decimal) -> bool:
    return token > 0


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


def detect_price_drops_from_reference(
    model_id: str,
    current_pricing: dict[str, str],
    *,
    reference_per_million: dict[str, Decimal],
    baseline_per_million: dict[str, Decimal] | None = None,
    thresholds: PriceDropThresholds,
) -> list[PriceDrop]:
    drops: list[PriceDrop] = []
    for field, reference in reference_per_million.items():
        if field not in current_pricing:
            continue
        if not _is_positive_price(reference):
            continue
        new_token = _parse_per_token(current_pricing[field])
        if new_token is None or not _is_known_price(new_token):
            continue
        new_per_million = new_token * Decimal(1_000_000)
        if not _is_positive_price(new_per_million):
            continue
        if new_per_million >= reference:
            continue
        if baseline_per_million is not None:
            baseline = baseline_per_million.get(field)
            if baseline is not None and new_per_million >= baseline:
                continue
        saved = reference - new_per_million
        pct_drop = saved / reference
        if pct_drop < thresholds.min_pct:
            continue
        if saved < thresholds.min_saved_per_million_usd:
            continue
        drops.append(
            PriceDrop(
                model_id=model_id,
                field=field,
                old_per_million_usd=reference,
                new_per_million_usd=new_per_million,
                pct_drop=pct_drop,
                saved_per_million_usd=saved,
            )
        )
    return drops
