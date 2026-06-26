from datetime import UTC, datetime
from decimal import Decimal

from modelwatch.history import (
    PriceHistoryPoint,
    PriceHistoryStore,
    append_build_to_history,
)
from modelwatch.pricing import (
    PriceDropThresholds,
    detect_price_drops_from_reference,
)
from modelwatch.pricing_glitch import (
    is_paid_zero_glitch_point,
    is_spurious_zero_drop_event,
    sanitize_history_fields,
)
from modelwatch.schemas import ModelPricing


def test_detect_price_drops_skips_zero_new_price_for_paid_models() -> None:
    drops = detect_price_drops_from_reference(
        model_id="deepseek/deepseek-chat",
        current_pricing={"prompt": "0", "completion": "0"},
        reference_per_million={
            "prompt": Decimal("0.200200"),
            "completion": Decimal("0.800100"),
        },
        thresholds=PriceDropThresholds(
            min_pct=Decimal("0.10"),
            min_saved_per_million_usd=Decimal("0.05"),
        ),
    )
    assert drops == []


def test_detect_price_drops_skips_zero_new_price_for_free_models() -> None:
    drops = detect_price_drops_from_reference(
        model_id="cohere/north-mini-code:free",
        current_pricing={"prompt": "0", "completion": "0"},
        reference_per_million={
            "prompt": Decimal("1"),
            "completion": Decimal("2"),
        },
        thresholds=PriceDropThresholds(
            min_pct=Decimal("0.10"),
            min_saved_per_million_usd=Decimal("0.05"),
        ),
    )
    assert drops == []


def test_append_history_skips_paid_zero_after_positive() -> None:
    at = datetime(2026, 6, 25, 13, 0, tzinfo=UTC)
    later = datetime(2026, 6, 25, 13, 30, tzinfo=UTC)
    store = PriceHistoryStore(generated_at=at, models={})
    paid = ModelPricing(prompt="0.0000002", completion="0.0000008")
    store = append_build_to_history(
        store,
        model_id="deepseek/deepseek-chat",
        pricing=paid,
        recorded_at=at,
    )
    glitch = ModelPricing(prompt="0", completion="0")
    updated = append_build_to_history(
        store,
        model_id="deepseek/deepseek-chat",
        pricing=glitch,
        recorded_at=later,
    )
    assert len(updated.models["deepseek/deepseek-chat"]) == 1


def test_is_paid_zero_glitch_point() -> None:
    points = [
        PriceHistoryPoint(
            recorded_at=datetime(2026, 6, 25, 13, 0, tzinfo=UTC),
            prompt_per_million=Decimal("0.200200"),
            completion_per_million=Decimal("0.800100"),
        ),
        PriceHistoryPoint(
            recorded_at=datetime(2026, 6, 25, 13, 30, tzinfo=UTC),
            prompt_per_million=Decimal("0"),
            completion_per_million=Decimal("0"),
        ),
        PriceHistoryPoint(
            recorded_at=datetime(2026, 6, 25, 14, 30, tzinfo=UTC),
            prompt_per_million=Decimal("0.200200"),
            completion_per_million=Decimal("0.800100"),
        ),
    ]
    assert is_paid_zero_glitch_point("deepseek/deepseek-chat", points, 1) is True
    assert is_paid_zero_glitch_point("cohere/north-mini-code:free", points, 1) is False


def test_is_spurious_zero_drop_event() -> None:
    assert is_spurious_zero_drop_event("deepseek/deepseek-chat", "0.000000") is True
    assert is_spurious_zero_drop_event("cohere/north-mini-code:free", "0") is False


def test_sanitize_history_fields_clears_zero_fields_with_positive_history() -> None:
    points = [
        PriceHistoryPoint(
            recorded_at=datetime(2026, 6, 25, 13, 0, tzinfo=UTC),
            prompt_per_million=Decimal("0.5"),
        ),
    ]
    fields = sanitize_history_fields(
        "deepseek/deepseek-chat",
        {"prompt": Decimal("0"), "completion": Decimal("0")},
        points,
    )
    assert fields["prompt"] is None
    assert fields["completion"] is None
