from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from modelwatch.pricing import PRICING_FIELDS, per_million_field_name

if TYPE_CHECKING:
    from modelwatch.history import PriceHistoryPoint


def is_free_model_id(model_id: str) -> bool:
    return model_id.endswith(":free") or model_id == "openrouter/free"


def _main_pricing_fields_zero(fields: dict[str, Decimal | None]) -> bool:
    prompt = fields.get("prompt")
    completion = fields.get("completion")
    return (prompt is None or prompt == 0) and (completion is None or completion == 0)


def _history_had_positive_main_pricing(points: list[PriceHistoryPoint]) -> bool:
    return any(_had_positive_main_pricing(point) for point in points)


def _recovers_to_positive_main_pricing_after(
    points: list[PriceHistoryPoint],
    index: int,
) -> bool:
    for later in points[index + 1 :]:
        if _had_positive_main_pricing(later):
            return True
    return False


def _settled_paid_to_free(existing_points: list[PriceHistoryPoint]) -> bool:
    if not existing_points or not _history_had_positive_main_pricing(existing_points):
        return False
    last_positive_idx = -1
    for index, point in enumerate(existing_points):
        if _had_positive_main_pricing(point):
            last_positive_idx = index
    if last_positive_idx < 0:
        return False
    tail = existing_points[last_positive_idx + 1 :]
    if not tail:
        return False
    return all(_has_zero_main_pricing(point) for point in tail)


def is_free_tier_model(
    model_id: str,
    *,
    pricing_fields: dict[str, Decimal | None] | None = None,
    existing_points: list[PriceHistoryPoint] | None = None,
) -> bool:
    if is_free_model_id(model_id):
        return True
    if pricing_fields is None or existing_points is None:
        return False
    if not _main_pricing_fields_zero(pricing_fields):
        return False
    if not _history_had_positive_main_pricing(existing_points):
        return True
    if _settled_paid_to_free(existing_points):
        return True
    return False


def is_spurious_zero_drop(model_id: str, new_per_million_usd: Decimal) -> bool:
    if is_free_model_id(model_id):
        return False
    return new_per_million_usd <= 0


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
    point = points[index]
    if is_free_tier_model(
        model_id,
        pricing_fields={
            "prompt": point.prompt_per_million,
            "completion": point.completion_per_million,
        },
        existing_points=points[:index],
    ):
        return False
    if not _has_zero_main_pricing(point):
        return False
    if not _history_had_positive_main_pricing(points[:index]):
        return False
    return _recovers_to_positive_main_pricing_after(points, index)


def sanitize_history_fields(
    model_id: str,
    fields: dict[str, Decimal | None],
    existing_points: list[PriceHistoryPoint],
) -> dict[str, Decimal | None]:
    if (
        is_free_tier_model(
            model_id,
            pricing_fields=fields,
            existing_points=existing_points,
        )
        or not existing_points
    ):
        return fields
    last = existing_points[-1]
    sanitized = dict(fields)
    for field in PRICING_FIELDS:
        if field in ("prompt", "completion"):
            continue
        value = sanitized.get(field)
        if value is None or value != 0:
            continue
        prior = getattr(last, per_million_field_name(field))
        if prior is not None and prior > 0:
            sanitized[field] = None
    return sanitized


def has_recordable_history_fields(fields: dict[str, Decimal | None]) -> bool:
    return any(fields.get(field) is not None for field in PRICING_FIELDS)
