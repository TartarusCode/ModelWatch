from datetime import UTC, datetime
from decimal import Decimal

from modelwatch.history import (
    PriceHistoryPoint,
    PriceHistoryStore,
    append_build_to_history,
    pricing_to_history_fields,
)
from modelwatch.schemas import ModelPricing


def test_pricing_to_history_fields_converts_tokens() -> None:
    pricing = ModelPricing(prompt="0.000003", completion="0.000015")
    fields = pricing_to_history_fields(pricing)
    assert fields["prompt"] == Decimal("3")
    assert fields["completion"] == Decimal("15")


def test_pricing_to_history_fields_marks_variable_as_none() -> None:
    pricing = ModelPricing(prompt="-1", completion="-1")
    fields = pricing_to_history_fields(pricing)
    assert fields["prompt"] is None
    assert fields["completion"] is None


def test_append_build_adds_point_per_model() -> None:
    at = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    store = PriceHistoryStore(generated_at=at, models={})
    pricing = ModelPricing(prompt="0.000002", completion="0.000010")
    updated = append_build_to_history(
        store,
        model_id="acme/model",
        pricing=pricing,
        recorded_at=at,
    )
    assert "acme/model" in updated.models
    assert len(updated.models["acme/model"]) == 1


def test_append_build_records_snapshot_on_every_build() -> None:
    at = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    pricing = ModelPricing(prompt="0.000002", completion="0.000010")
    point = PriceHistoryPoint(
        recorded_at=at,
        prompt_per_million=Decimal("2"),
        completion_per_million=Decimal("10"),
    )
    store = PriceHistoryStore(
        generated_at=at,
        models={"acme/model": [point]},
    )
    later = datetime(2026, 5, 29, 12, 30, tzinfo=UTC)
    updated = append_build_to_history(
        store,
        model_id="acme/model",
        pricing=pricing,
        recorded_at=later,
    )
    assert len(updated.models["acme/model"]) == 2
    assert updated.models["acme/model"][-1].recorded_at == later


def test_append_build_records_cache_read_in_history() -> None:
    at = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    store = PriceHistoryStore(generated_at=at, models={})
    pricing = ModelPricing(
        prompt="0.000002",
        completion="0.000010",
        input_cache_read="0.0000005",
    )
    updated = append_build_to_history(
        store,
        model_id="acme/model",
        pricing=pricing,
        recorded_at=at,
    )
    point = updated.models["acme/model"][0]
    assert point.input_cache_read_per_million == Decimal("0.5")


def test_append_build_records_price_change() -> None:
    at = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    pricing = ModelPricing(prompt="0.000002", completion="0.000010")
    point = PriceHistoryPoint(
        recorded_at=at,
        prompt_per_million=Decimal("2"),
        completion_per_million=Decimal("10"),
    )
    store = PriceHistoryStore(
        generated_at=at,
        models={"acme/model": [point]},
    )
    later = datetime(2026, 5, 29, 12, 30, tzinfo=UTC)
    new_pricing = ModelPricing(prompt="0.000001", completion="0.000010")
    updated = append_build_to_history(
        store,
        model_id="acme/model",
        pricing=new_pricing,
        recorded_at=later,
    )
    assert len(updated.models["acme/model"]) == 2
