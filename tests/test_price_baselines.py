from datetime import UTC, datetime, timedelta
from decimal import Decimal

from modelwatch.history import PriceHistoryPoint
from modelwatch.price_baselines import (
    MA_WINDOW_DAYS,
    MIN_MA_POINTS,
    apply_drop_ratchet,
    compute_moving_average_per_field,
    reference_price,
)
from modelwatch.pricing import PriceDrop
from modelwatch.schemas import PriceDropBaselinesStore


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


def test_reference_price_uses_ma_when_no_baseline() -> None:
    assert reference_price(Decimal("3"), None) == Decimal("3")


def test_reference_price_uses_max_of_ma_and_baseline() -> None:
    assert reference_price(Decimal("2.80"), Decimal("2.50")) == Decimal("2.80")
    assert reference_price(Decimal("2.40"), Decimal("2.50")) == Decimal("2.50")


def test_apply_drop_ratchet_updates_baseline() -> None:
    at = datetime(2026, 6, 23, 12, 0, tzinfo=UTC)
    store = PriceDropBaselinesStore(generated_at=at, models={})
    drops = [
        PriceDrop(
            model_id="acme/model",
            field="prompt",
            old_per_million_usd=Decimal("3"),
            new_per_million_usd=Decimal("2.5"),
            pct_drop=Decimal("0.1666666666666666666666666667"),
            saved_per_million_usd=Decimal("0.5"),
        )
    ]

    updated = apply_drop_ratchet(store, drops, updated_at=at)

    assert updated.models["acme/model"]["prompt"] == "2.500000"


def test_apply_drop_ratchet_only_ratchets_down() -> None:
    at = datetime(2026, 6, 23, 12, 0, tzinfo=UTC)
    store = PriceDropBaselinesStore(
        generated_at=at,
        models={"acme/model": {"prompt": "2.000000"}},
    )
    drops = [
        PriceDrop(
            model_id="acme/model",
            field="prompt",
            old_per_million_usd=Decimal("3"),
            new_per_million_usd=Decimal("2.5"),
            pct_drop=Decimal("0.1666666666666666666666666667"),
            saved_per_million_usd=Decimal("0.5"),
        )
    ]

    updated = apply_drop_ratchet(store, drops, updated_at=at)

    assert updated.models["acme/model"]["prompt"] == "2.000000"
