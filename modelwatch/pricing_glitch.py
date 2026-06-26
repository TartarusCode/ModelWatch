from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from modelwatch.pricing import PRICING_FIELDS

if TYPE_CHECKING:
    from modelwatch.history import PriceHistoryPoint


def _per_million_field_name(field: str) -> str:
    return f"{field}_per_million"


def is_free_model_id(model_id: str) -> bool:
    return model_id.endswith(":free") or model_id == "openrouter/free"


def is_zero_price(value: Decimal | None) -> bool:
    return value is not None and value == 0


def is_spurious_zero_drop(model_id: str, new_per_million_usd: Decimal) -> bool:
    return not is_free_model_id(model_id) and new_per_million_usd <= 0


def is_spurious_zero_drop_event(model_id: str, new_per_million_usd: str) -> bool:
    try:
        value = Decimal(new_per_million_usd)
    except Exception:
        return False
    return is_spurious_zero_drop(model_id, value)


def _had_positive_main_pricing(point: PriceHistoryPoint | None) -> bool:
    if point is None:
        return False
    prompt = point.prompt_per_million
    completion = point.completion_per_million
    return (prompt is not None and prompt > 0) or (
        completion is not None and completion > 0
    )


def _has_zero_main_pricing(point: PriceHistoryPoint) -> bool:
    prompt = point.prompt_per_million
    completion = point.completion_per_million
    prompt_zero = prompt is None or prompt == 0
    completion_zero = completion is None or completion == 0
    return prompt_zero and completion_zero


def is_paid_zero_glitch_point(
    model_id: str,
    points: list[PriceHistoryPoint],
    index: int,
) -> bool:
    if is_free_model_id(model_id):
        return False
    point = points[index]
    if not _has_zero_main_pricing(point):
        return False
    before = points[index - 1] if index > 0 else None
    after = points[index + 1] if index + 1 < len(points) else None
    return _had_positive_main_pricing(before) or _had_positive_main_pricing(after)


def sanitize_history_fields(
    model_id: str,
    fields: dict[str, Decimal | None],
    existing_points: list[PriceHistoryPoint],
) -> dict[str, Decimal | None]:
    if is_free_model_id(model_id) or not existing_points:
        return fields
    last = existing_points[-1]
    sanitized = dict(fields)
    if _had_positive_main_pricing(last):
        for field in ("prompt", "completion"):
            if sanitized.get(field) == 0:
                sanitized[field] = None
    for field in PRICING_FIELDS:
        if field in ("prompt", "completion"):
            continue
        value = sanitized.get(field)
        if value is None or value != 0:
            continue
        prior = getattr(last, _per_million_field_name(field))
        if prior is not None and prior > 0:
            sanitized[field] = None
    return sanitized


def has_recordable_history_fields(fields: dict[str, Decimal | None]) -> bool:
    return any(fields.get(field) is not None for field in PRICING_FIELDS)
