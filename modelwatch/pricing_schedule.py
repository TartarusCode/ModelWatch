"""Time-of-day pricing schedules (OpenRouter ``pricing.overrides``).

OpenRouter's models API reports ``pricing`` for the window that is active right
now, and repeats the full weekly schedule under ``pricing.overrides``. Models
with peak/off-peak pricing (DeepSeek, Tencent, ...) therefore appear to change
price every time a window boundary passes, even though their rate card is
unchanged.

``overrides`` mixes two kinds of entry and only one of them is a schedule:
time windows (``utc_days`` / ``utc_start`` / ``utc_end``) and long-context
tiers (``min_prompt_tokens``). Only time windows are parsed here.

This module derives a window-independent view of that rate card so the rest of
the pipeline compares like with like:

- ``standard``: the highest scheduled rate per field, i.e. the rate charged
  outside any discount window. Used as the canonical price for change
  detection, history and moving averages.
- ``minimum``: the cheapest scheduled rate per field (the deepest discount).

A real rate-card change moves ``standard``; a model merely entering its peak or
off-peak window does not.
"""

from __future__ import annotations

from decimal import Decimal

from modelwatch.price_parsing import is_known_price, parse_per_token
from modelwatch.pricing import PRICING_FIELDS, per_million_usd
from modelwatch.schemas import ModelPricing, ModelSnapshot, PricingSchedule
from modelwatch.schemas import PricingScheduleWindow as ScheduleWindow

_WEEKDAY_ORDER = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
_DAY_ABBREVIATIONS = {
    "monday": "Mon",
    "tuesday": "Tue",
    "wednesday": "Wed",
    "thursday": "Thu",
    "friday": "Fri",
    "saturday": "Sat",
    "sunday": "Sun",
}
_WEEKDAYS = frozenset(_WEEKDAY_ORDER[:5])
_WEEKEND = frozenset(_WEEKDAY_ORDER[5:])
_ALL_DAYS = frozenset(_WEEKDAY_ORDER)


def _clean_rate(value: object) -> str | None:
    """Return ``value`` when it is a displayable per-token price, else ``None``."""
    if not isinstance(value, str):
        return None
    token = parse_per_token(value)
    if token is None or not is_known_price(token):
        return None
    return value


def _format_days(utc_days: list[str] | None) -> str:
    if not utc_days:
        return "Every day"
    days = {day.lower() for day in utc_days}
    if days == _ALL_DAYS:
        return "Every day"
    if days == _WEEKDAYS:
        return "Mon–Fri"
    if days == _WEEKEND:
        return "Sat–Sun"
    ordered = [day for day in _WEEKDAY_ORDER if day in days]
    return ", ".join(_DAY_ABBREVIATIONS[day] for day in ordered)


def _format_clock(value: int) -> str:
    """OpenRouter sends clock values as HHMM (``100`` = 01:00 UTC, ``1630`` = 16:30)."""
    return f"{value // 100:02d}:{value % 100:02d}"


def window_label(
    utc_days: list[str] | None,
    utc_start: int | None,
    utc_end: int | None,
) -> str:
    """Human-readable window label, e.g. ``Mon–Fri 01:00–04:00 UTC``."""
    days = _format_days(utc_days)
    if utc_start is None and utc_end is None:
        return f"{days} all day UTC"
    start = _format_clock(utc_start or 0)
    end = "24:00" if not utc_end else _format_clock(utc_end)
    return f"{days} {start}–{end} UTC"


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _days_or_none(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    days = [day for day in value if isinstance(day, str)]
    return days or None


def _is_time_window(entry: dict[str, object]) -> bool:
    """True for time-of-day windows; False for context-length tiers.

    ``pricing.overrides`` carries both kinds of entry: those keyed by
    ``utc_days`` / ``utc_start`` / ``utc_end`` are time windows, while those
    keyed by ``min_prompt_tokens`` are long-context tiers (e.g. Claude charging
    double above 200k tokens). Tiers do not move with the clock, so folding
    them into the standard rate would track the long-context price instead of
    the model's headline rate.
    """
    return any(key in entry for key in ("utc_days", "utc_start", "utc_end"))


def pricing_schedule_from_raw(raw_pricing: object) -> PricingSchedule | None:
    """Build a :class:`PricingSchedule` from a raw models-API pricing object.

    Returns ``None`` when the model has no usable ``overrides`` (no time-of-day
    schedule), in which case the top-level price is the whole story.
    """
    if not isinstance(raw_pricing, dict):
        return None
    raw_overrides = raw_pricing.get("overrides")
    if not isinstance(raw_overrides, list):
        return None

    windows: list[ScheduleWindow] = []
    for entry in raw_overrides:
        if not isinstance(entry, dict):
            continue
        if not _is_time_window(entry):
            continue
        window_rates = {
            field: rate
            for field in PRICING_FIELDS
            if (rate := _clean_rate(entry.get(field))) is not None
        }
        if not window_rates:
            continue
        utc_days = _days_or_none(entry.get("utc_days"))
        utc_start = _int_or_none(entry.get("utc_start"))
        utc_end = _int_or_none(entry.get("utc_end"))
        windows.append(
            ScheduleWindow(
                label=window_label(utc_days, utc_start, utc_end),
                utc_days=utc_days,
                utc_start=utc_start,
                utc_end=utc_end,
                rates=window_rates,
            ),
        )
    if not windows:
        return None

    standard: dict[str, str] = {}
    minimum: dict[str, str] = {}
    rates_by_field: dict[str, list[str]] = {}
    for field in PRICING_FIELDS:
        candidates = [
            rate
            for rate in (
                [_clean_rate(raw_pricing.get(field))]
                + [window.rates.get(field) for window in windows]
            )
            if rate is not None
        ]
        if not candidates:
            continue
        # Dedupe by numeric value; keep the first spelling for each rate.
        by_value: dict[Decimal, str] = {}
        for rate in candidates:
            value = per_million_usd(rate)
            by_value.setdefault(value, rate)
        ordered = [by_value[value] for value in sorted(by_value)]
        rates_by_field[field] = ordered
        minimum[field] = ordered[0]
        standard[field] = ordered[-1]

    if not standard:
        return None
    return PricingSchedule(
        standard=standard,
        minimum=minimum,
        rates=rates_by_field,
        windows=windows,
    )


def has_schedule(snapshot: ModelSnapshot) -> bool:
    return snapshot.pricing_schedule is not None


def per_million_or_none(per_token: str | None) -> Decimal | None:
    if per_token is None:
        return None
    try:
        return per_million_usd(per_token)
    except ValueError:
        return None


def scheduled_rates_per_million(
    schedule: PricingSchedule,
) -> dict[str, tuple[Decimal, ...]]:
    """Every distinct rate the schedule can charge per field, USD per 1M."""
    return {
        field: tuple(
            value
            for value in (per_million_or_none(rate) for rate in rates)
            if value is not None
        )
        for field, rates in schedule.rates.items()
    }


def standard_per_million(snapshot: ModelSnapshot) -> dict[str, Decimal]:
    """Canonical window-independent price per field, in USD per 1M tokens.

    Falls back to the snapshot's current (window-dependent) price for fields
    the schedule does not cover.
    """
    raw = snapshot.pricing.model_dump()
    schedule = snapshot.pricing_schedule
    result: dict[str, Decimal] = {}
    for field in PRICING_FIELDS:
        source = raw.get(field)
        if schedule is not None and field in schedule.standard:
            source = schedule.standard[field]
        value = per_million_or_none(source if isinstance(source, str) else None)
        if value is not None:
            result[field] = value
    return result


def discount_per_million(snapshot: ModelSnapshot) -> dict[str, Decimal]:
    """Cheapest scheduled rate per field, where it is below the standard rate.

    Empty for models without a time-of-day discount, which keeps unscheduled
    models on a single (standard) price track.
    """
    schedule = snapshot.pricing_schedule
    if schedule is None:
        return {}
    result: dict[str, Decimal] = {}
    for field, rate in schedule.minimum.items():
        minimum = per_million_or_none(rate)
        standard = per_million_or_none(schedule.standard.get(field))
        if minimum is None or standard is None or minimum >= standard:
            continue
        result[field] = minimum
    return result


def standard_pricing(snapshot: ModelSnapshot) -> ModelPricing:
    """Copy of ``snapshot.pricing`` with every scheduled field set to its
    standard rate, so history and moving averages are window-independent."""
    schedule = snapshot.pricing_schedule
    if schedule is None:
        return snapshot.pricing
    updates = {
        field: rate
        for field, rate in schedule.standard.items()
        if field in PRICING_FIELDS
    }
    if not updates:
        return snapshot.pricing
    return snapshot.pricing.model_copy(update=updates)
