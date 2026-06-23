from decimal import Decimal

import pytest

from modelwatch.pricing import (
    PriceDropThresholds,
    detect_price_drops_from_reference,
    per_million_usd,
    pricing_fields_to_compare,
)


def _thresholds() -> PriceDropThresholds:
    return PriceDropThresholds(
        min_pct=Decimal("0.10"),
        min_saved_per_million_usd=Decimal("0.05"),
    )


def _reference_from_old(old_pricing: dict[str, str]) -> dict[str, Decimal]:
    return {
        field: per_million_usd(old_pricing[field])
        for field in old_pricing
        if field in old_pricing
    }


def test_per_million_usd_converts_per_token_string() -> None:
    assert per_million_usd("0.000008") == Decimal("8")


def test_detect_significant_prompt_drop_when_thresholds_met() -> None:
    old_pricing = {"prompt": "0.000003", "completion": "0.000015"}
    new_pricing = {"prompt": "0.000002", "completion": "0.000015"}

    drops = detect_price_drops_from_reference(
        model_id="acme/model",
        current_pricing=new_pricing,
        reference_per_million=_reference_from_old(old_pricing),
        thresholds=_thresholds(),
    )

    assert len(drops) == 1
    assert drops[0].field == "prompt"
    assert drops[0].pct_drop >= Decimal("0.10")
    assert drops[0].saved_per_million_usd >= Decimal("0.05")


def test_ignores_price_increases() -> None:
    old_pricing = {"prompt": "0.000002", "completion": "0.000015"}
    new_pricing = {"prompt": "0.000003", "completion": "0.000015"}

    drops = detect_price_drops_from_reference(
        model_id="acme/model",
        current_pricing=new_pricing,
        reference_per_million=_reference_from_old(old_pricing),
        thresholds=_thresholds(),
    )

    assert drops == []


def test_ignores_drop_below_pct_threshold() -> None:
    old_pricing = {"prompt": "0.000010", "completion": "0.000015"}
    new_pricing = {"prompt": "0.0000095", "completion": "0.000015"}

    drops = detect_price_drops_from_reference(
        model_id="acme/model",
        current_pricing=new_pricing,
        reference_per_million=_reference_from_old(old_pricing),
        thresholds=_thresholds(),
    )

    assert drops == []


def test_ignores_drop_below_absolute_savings_threshold() -> None:
    old_pricing = {"prompt": "0.00000010", "completion": "0.000015"}
    new_pricing = {"prompt": "0.00000008", "completion": "0.000015"}

    drops = detect_price_drops_from_reference(
        model_id="acme/model",
        current_pricing=new_pricing,
        reference_per_million=_reference_from_old(old_pricing),
        thresholds=_thresholds(),
    )

    assert drops == []


def test_ignores_zero_reference_price() -> None:
    new_pricing = {"prompt": "0", "completion": "0.000010"}
    reference = {"prompt": Decimal("0"), "completion": Decimal("15")}

    drops = detect_price_drops_from_reference(
        model_id="acme/model",
        current_pricing=new_pricing,
        reference_per_million=reference,
        thresholds=_thresholds(),
    )

    assert all(drop.field != "prompt" for drop in drops)
    assert len(drops) == 1
    assert drops[0].field == "completion"


def test_compares_optional_pricing_fields_when_present() -> None:
    fields = pricing_fields_to_compare(
        {"prompt": "1", "completion": "2", "image": "3"},
        {"prompt": "1", "completion": "2"},
    )
    assert fields == ("prompt", "completion")


def test_ignores_variable_price_sentinel() -> None:
    new_pricing = {"prompt": "-1", "completion": "-1"}
    reference = {"prompt": Decimal("3"), "completion": Decimal("15")}

    drops = detect_price_drops_from_reference(
        model_id="openrouter/auto",
        current_pricing=new_pricing,
        reference_per_million=reference,
        thresholds=_thresholds(),
    )

    assert drops == []


def test_per_million_usd_rejects_variable_sentinel() -> None:
    with pytest.raises(ValueError, match="not a displayable price"):
        per_million_usd("-1")


def test_detects_completion_drop() -> None:
    old_pricing = {"prompt": "0.000003", "completion": "0.000020"}
    new_pricing = {"prompt": "0.000003", "completion": "0.000010"}

    drops = detect_price_drops_from_reference(
        model_id="acme/model",
        current_pricing=new_pricing,
        reference_per_million=_reference_from_old(old_pricing),
        thresholds=_thresholds(),
    )

    assert len(drops) == 1
    assert drops[0].field == "completion"
