from datetime import datetime, timedelta
from decimal import Decimal

from modelwatch.history import PriceHistoryPoint
from modelwatch.pricing import PRICING_FIELDS, per_million_field_name

MA_WINDOW_DAYS = 7
MIN_MA_POINTS = 3


def compute_moving_average_per_field(
    history_points: list[PriceHistoryPoint],
    *,
    now: datetime,
    window_days: int = MA_WINDOW_DAYS,
    min_points: int = MIN_MA_POINTS,
) -> dict[str, Decimal]:
    cutoff = now - timedelta(days=window_days)
    in_window = [point for point in history_points if point.recorded_at >= cutoff]
    if len(in_window) < min_points:
        return {}

    averages: dict[str, Decimal] = {}
    for field in PRICING_FIELDS:
        attr = per_million_field_name(field)
        values = [
            value
            for point in in_window
            if (value := getattr(point, attr)) is not None and value > 0
        ]
        if len(values) < min_points:
            continue
        averages[field] = sum(values, start=Decimal(0)) / Decimal(len(values))
    return averages
