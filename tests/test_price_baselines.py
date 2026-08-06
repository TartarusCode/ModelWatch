from datetime import UTC, datetime, timedelta
from decimal import Decimal

from modelwatch.history import PriceHistoryPoint
from modelwatch.price_baselines import (
    MA_WINDOW_DAYS,
    MIN_MA_POINTS,
    compute_moving_average_per_field,
)


def _point(
    *,
    recorded_at: datetime,
    prompt: Decimal | None = None,
    completion: Decimal | None = None,
) -> PriceHistoryPoint:
    return PriceHistoryPoint(
        recorded_at=recorded_at,
        prompt_per_million=prompt,
        completion_per_million=completion,
    )


def test_ma_uses_only_points_within_7_day_window() -> None:
    now = datetime(2026, 6, 23, 12, 0, tzinfo=UTC)
    old = now - timedelta(days=MA_WINDOW_DAYS, hours=1)
    recent = now - timedelta(days=1)
    points = [
        _point(recorded_at=old, prompt=Decimal("10")),
        _point(recorded_at=recent, prompt=Decimal("3")),
        _point(recorded_at=recent + timedelta(hours=1), prompt=Decimal("3")),
        _point(recorded_at=recent + timedelta(hours=2), prompt=Decimal("3")),
    ]

    ma = compute_moving_average_per_field(
        points,
        now=now,
        window_days=MA_WINDOW_DAYS,
    )

    assert ma["prompt"] == Decimal("3")


def test_insufficient_history_returns_empty_ma() -> None:
    now = datetime(2026, 6, 23, 12, 0, tzinfo=UTC)
    recent = now - timedelta(days=1)
    points = [
        _point(recorded_at=recent, prompt=Decimal("3")),
        _point(recorded_at=recent + timedelta(hours=1), prompt=Decimal("3")),
    ]

    ma = compute_moving_average_per_field(
        points,
        now=now,
        window_days=MA_WINDOW_DAYS,
        min_points=MIN_MA_POINTS,
    )

    assert ma == {}
