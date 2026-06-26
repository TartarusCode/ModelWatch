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
    is_free_tier_model,
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


def test_append_history_records_zero_for_preview_without_free_tag() -> None:
    at = datetime(2026, 6, 25, 13, 0, tzinfo=UTC)
    store = PriceHistoryStore(generated_at=at, models={})
    free_preview = ModelPricing(prompt="0", completion="0")
    updated = append_build_to_history(
        store,
        model_id="google/lyria-3-clip-preview",
        pricing=free_preview,
        recorded_at=at,
    )
    assert len(updated.models["google/lyria-3-clip-preview"]) == 1


def test_is_free_tier_model_preview_without_free_tag() -> None:
    assert is_free_tier_model(
        "google/lyria-3-clip-preview",
        pricing_fields={"prompt": Decimal("0"), "completion": Decimal("0")},
        existing_points=[],
    )


def test_is_free_tier_model_glitch_zero_after_positive_history() -> None:
    points = [
        PriceHistoryPoint(
            recorded_at=datetime(2026, 6, 25, 13, 0, tzinfo=UTC),
            prompt_per_million=Decimal("0.200200"),
        ),
    ]
    assert is_free_tier_model(
        "deepseek/deepseek-chat",
        pricing_fields={"prompt": Decimal("0"), "completion": Decimal("0")},
        existing_points=points,
    ) is False


def test_is_free_tier_model_after_settled_paid_to_free_transition() -> None:
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
    ]
    assert is_free_tier_model(
        "acme/former-paid",
        pricing_fields={"prompt": Decimal("0"), "completion": Decimal("0")},
        existing_points=points,
    ) is True


def test_append_history_records_paid_to_free_transition() -> None:
    at = datetime(2026, 6, 25, 13, 0, tzinfo=UTC)
    later = datetime(2026, 6, 25, 13, 30, tzinfo=UTC)
    store = PriceHistoryStore(generated_at=at, models={})
    paid = ModelPricing(prompt="0.0000002", completion="0.0000008")
    store = append_build_to_history(
        store,
        model_id="acme/former-paid",
        pricing=paid,
        recorded_at=at,
    )
    free = ModelPricing(prompt="0", completion="0")
    updated = append_build_to_history(
        store,
        model_id="acme/former-paid",
        pricing=free,
        recorded_at=later,
    )
    assert len(updated.models["acme/former-paid"]) == 2
    assert updated.models["acme/former-paid"][-1].prompt_per_million == 0


def test_append_history_skips_paid_zero_after_positive() -> None:
    at = datetime(2026, 6, 25, 13, 0, tzinfo=UTC)
    later = datetime(2026, 6, 25, 13, 30, tzinfo=UTC)
    recovered = datetime(2026, 6, 25, 14, 30, tzinfo=UTC)
    store = PriceHistoryStore(generated_at=at, models={})
    paid = ModelPricing(prompt="0.0000002", completion="0.0000008")
    store = append_build_to_history(
        store,
        model_id="deepseek/deepseek-chat",
        pricing=paid,
        recorded_at=at,
    )
    glitch = ModelPricing(prompt="0", completion="0")
    store = append_build_to_history(
        store,
        model_id="deepseek/deepseek-chat",
        pricing=glitch,
        recorded_at=later,
    )
    restored = ModelPricing(prompt="0.0000002", completion="0.0000008")
    updated = append_build_to_history(
        store,
        model_id="deepseek/deepseek-chat",
        pricing=restored,
        recorded_at=recovered,
    )
    points = updated.models["deepseek/deepseek-chat"]
    assert len(points) == 3
    assert is_paid_zero_glitch_point("deepseek/deepseek-chat", points, 1) is True


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


def test_is_paid_zero_glitch_point_false_for_settled_paid_to_free_tail() -> None:
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
            recorded_at=datetime(2026, 6, 25, 14, 0, tzinfo=UTC),
            prompt_per_million=Decimal("0"),
            completion_per_million=Decimal("0"),
        ),
    ]
    assert is_paid_zero_glitch_point("acme/former-paid", points, 1) is False
    assert is_paid_zero_glitch_point("acme/former-paid", points, 2) is False


def test_is_spurious_zero_drop_event() -> None:
    assert is_spurious_zero_drop_event("deepseek/deepseek-chat", "0.000000") is True
    assert is_spurious_zero_drop_event("cohere/north-mini-code:free", "0") is False


def test_sanitize_history_fields_preserves_main_zero_for_paid_to_free() -> None:
    points = [
        PriceHistoryPoint(
            recorded_at=datetime(2026, 6, 25, 13, 0, tzinfo=UTC),
            prompt_per_million=Decimal("0.5"),
        ),
    ]
    fields = sanitize_history_fields(
        "acme/former-paid",
        {"prompt": Decimal("0"), "completion": Decimal("0")},
        points,
    )
    assert fields["prompt"] == 0
    assert fields["completion"] == 0


def test_sanitize_history_fields_clears_zero_cache_after_positive_history() -> None:
    points = [
        PriceHistoryPoint(
            recorded_at=datetime(2026, 6, 25, 13, 0, tzinfo=UTC),
            prompt_per_million=Decimal("0.5"),
            input_cache_read_per_million=Decimal("0.1"),
        ),
    ]
    fields = sanitize_history_fields(
        "deepseek/deepseek-chat",
        {
            "prompt": Decimal("0.2"),
            "completion": Decimal("0.8"),
            "input_cache_read": Decimal("0"),
        },
        points,
    )
    assert fields["prompt"] == Decimal("0.2")
    assert fields["input_cache_read"] is None
