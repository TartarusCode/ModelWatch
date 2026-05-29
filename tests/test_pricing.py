from decimal import Decimal

import pytest

from modelwatch.pricing import (
    PriceDropThresholds,
    detect_price_drops,
    per_million_usd,
    pricing_fields_to_compare,
)


def test_per_million_usd_converts_per_token_string() -> None:
    assert per_million_usd("0.000008") == Decimal("8")


def test_detect_significant_prompt_drop_when_thresholds_met() -> None:
    old_pricing = {"prompt": "0.000003", "completion": "0.000015"}
    new_pricing = {"prompt": "0.000002", "completion": "0.000015"}
    thresholds = PriceDropThresholds(
        min_pct=Decimal("0.10"),
        min_saved_per_million_usd=Decimal("0.05"),
    )

    drops = detect_price_drops(
        model_id="acme/model",
        old_pricing=old_pricing,
        new_pricing=new_pricing,
        thresholds=thresholds,
    )

    assert len(drops) == 1
    assert drops[0].field == "prompt"
    assert drops[0].pct_drop >= Decimal("0.10")
    assert drops[0].saved_per_million_usd >= Decimal("0.05")


def test_ignores_price_increases() -> None:
    old_pricing = {"prompt": "0.000002", "completion": "0.000015"}
    new_pricing = {"prompt": "0.000003", "completion": "0.000015"}
    thresholds = PriceDropThresholds(
        min_pct=Decimal("0.10"),
        min_saved_per_million_usd=Decimal("0.05"),
    )

    drops = detect_price_drops(
        model_id="acme/model",
        old_pricing=old_pricing,
        new_pricing=new_pricing,
        thresholds=thresholds,
    )

    assert drops == []


def test_ignores_drop_below_pct_threshold() -> None:
    old_pricing = {"prompt": "0.000010", "completion": "0.000015"}
    new_pricing = {"prompt": "0.0000095", "completion": "0.000015"}
    thresholds = PriceDropThresholds(
        min_pct=Decimal("0.10"),
        min_saved_per_million_usd=Decimal("0.05"),
    )

    drops = detect_price_drops(
        model_id="acme/model",
        old_pricing=old_pricing,
        new_pricing=new_pricing,
        thresholds=thresholds,
    )

    assert drops == []


def test_ignores_drop_below_absolute_savings_threshold() -> None:
    old_pricing = {"prompt": "0.00000010", "completion": "0.000015"}
    new_pricing = {"prompt": "0.00000008", "completion": "0.000015"}
    thresholds = PriceDropThresholds(
        min_pct=Decimal("0.10"),
        min_saved_per_million_usd=Decimal("0.05"),
    )

    drops = detect_price_drops(
        model_id="acme/model",
        old_pricing=old_pricing,
        new_pricing=new_pricing,
        thresholds=thresholds,
    )

    assert drops == []


def test_ignores_zero_old_price() -> None:
    old_pricing = {"prompt": "0", "completion": "0.000015"}
    new_pricing = {"prompt": "0", "completion": "0.000010"}
    thresholds = PriceDropThresholds(
        min_pct=Decimal("0.10"),
        min_saved_per_million_usd=Decimal("0.05"),
    )

    drops = detect_price_drops(
        model_id="acme/model",
        old_pricing=old_pricing,
        new_pricing=new_pricing,
        thresholds=thresholds,
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
    old_pricing = {"prompt": "0.000003", "completion": "0.000015"}
    new_pricing = {"prompt": "-1", "completion": "-1"}
    thresholds = PriceDropThresholds(
        min_pct=Decimal("0.10"),
        min_saved_per_million_usd=Decimal("0.05"),
    )

    drops = detect_price_drops(
        model_id="openrouter/auto",
        old_pricing=old_pricing,
        new_pricing=new_pricing,
        thresholds=thresholds,
    )

    assert drops == []


def test_per_million_usd_rejects_variable_sentinel() -> None:
    with pytest.raises(ValueError, match="not a displayable price"):
        per_million_usd("-1")


def test_detects_completion_drop() -> None:
    old_pricing = {"prompt": "0.000003", "completion": "0.000020"}
    new_pricing = {"prompt": "0.000003", "completion": "0.000010"}
    thresholds = PriceDropThresholds(
        min_pct=Decimal("0.10"),
        min_saved_per_million_usd=Decimal("0.05"),
    )

    drops = detect_price_drops(
        model_id="acme/model",
        old_pricing=old_pricing,
        new_pricing=new_pricing,
        thresholds=thresholds,
    )

    assert len(drops) == 1
    assert drops[0].field == "completion"
