from datetime import UTC, datetime, timedelta
from decimal import Decimal

from modelwatch.history import PriceHistoryPoint
from modelwatch.price_baselines import (
    MA_WINDOW_DAYS,
    MIN_MA_POINTS,
    canonicalize_points_for_standard,
    compute_moving_average_per_field,
)
from modelwatch.pricing_schedule import pricing_schedule_from_raw

# deepseek/deepseek-v4.1-flash shape: off-peak $0.15/$0.60, weekday peak
# $0.30/$1.20 (windows are HHMM UTC values).
SCHEDULE_RAW = {
    "prompt": "0.00000015",
    "completion": "0.0000006",
    "overrides": [
        {
            "utc_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "utc_start": 100,
            "utc_end": 400,
            "prompt": "0.0000003",
            "completion": "0.0000012",
        },
    ],
}


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


def test_canonicalize_maps_scheduled_rates_onto_the_standard_rate() -> None:
    now = datetime(2026, 6, 23, 12, 0, tzinfo=UTC)
    schedule = pricing_schedule_from_raw(SCHEDULE_RAW)
    points = [
        _point(
            recorded_at=now - timedelta(days=2),
            prompt=Decimal("0.15"),
            completion=Decimal("0.6"),
        ),
        _point(
            recorded_at=now - timedelta(days=1),
            prompt=Decimal("0.3"),
            completion=Decimal("1.2"),
        ),
        _point(recorded_at=now, prompt=Decimal("0.15"), completion=Decimal("0.6")),
    ]

    canonicalized = canonicalize_points_for_standard(points, schedule)

    assert [point.prompt_per_million for point in canonicalized] == [
        Decimal("0.3"),
        Decimal("0.3"),
        Decimal("0.3"),
    ]
    assert [point.completion_per_million for point in canonicalized] == [
        Decimal("1.2"),
        Decimal("1.2"),
        Decimal("1.2"),
    ]


def test_canonicalize_keeps_prices_that_are_not_scheduled_rates() -> None:
    now = datetime(2026, 6, 23, 12, 0, tzinfo=UTC)
    schedule = pricing_schedule_from_raw(SCHEDULE_RAW)
    points = [
        _point(recorded_at=now - timedelta(days=2), prompt=Decimal("0.42")),
        _point(recorded_at=now, prompt=Decimal("0.3")),
    ]

    canonicalized = canonicalize_points_for_standard(points, schedule)

    assert [point.prompt_per_million for point in canonicalized] == [
        Decimal("0.42"),
        Decimal("0.3"),
    ]


def test_canonicalize_is_a_no_op_without_schedule() -> None:
    now = datetime(2026, 6, 23, 12, 0, tzinfo=UTC)
    points = [_point(recorded_at=now, prompt=Decimal("0.15"))]

    assert canonicalize_points_for_standard(points, None) is points


def test_moving_average_of_flapping_scheduled_model_is_stable() -> None:
    """Alternating peak/off-peak points must not drag the 7-day MA around."""
    now = datetime(2026, 6, 23, 12, 0, tzinfo=UTC)
    schedule = pricing_schedule_from_raw(SCHEDULE_RAW)
    points = [
        _point(
            recorded_at=now - timedelta(hours=offset),
            prompt=Decimal("0.15") if offset % 2 else Decimal("0.3"),
        )
        for offset in range(6)
    ]

    raw_ma = compute_moving_average_per_field(points, now=now)
    canonical_ma = compute_moving_average_per_field(
        canonicalize_points_for_standard(points, schedule),
        now=now,
    )

    assert raw_ma["prompt"] == Decimal("0.225")
    assert canonical_ma["prompt"] == Decimal("0.3")
