from decimal import Decimal

from modelwatch.pricing import (
    PriceDropThresholds,
    detect_price_drops_from_reference,
)


def _thresholds() -> PriceDropThresholds:
    return PriceDropThresholds(
        min_pct=Decimal("0.10"),
        min_saved_per_million_usd=Decimal("0.05"),
    )


def test_spike_and_return_does_not_trigger() -> None:
    current_pricing = {"prompt": "0.000003", "completion": "0.000015"}
    reference = {"prompt": Decimal("3")}

    drops = detect_price_drops_from_reference(
        model_id="acme/model",
        current_pricing=current_pricing,
        reference_per_million=reference,
        thresholds=_thresholds(),
    )

    assert drops == []


def test_true_drop_from_stable_ma_triggers() -> None:
    current_pricing = {"prompt": "0.0000025", "completion": "0.000015"}
    reference = {"prompt": Decimal("3")}

    drops = detect_price_drops_from_reference(
        model_id="acme/model",
        current_pricing=current_pricing,
        reference_per_million=reference,
        thresholds=_thresholds(),
    )

    assert len(drops) == 1
    assert drops[0].field == "prompt"
    assert drops[0].old_per_million_usd == Decimal("3")
    assert drops[0].new_per_million_usd == Decimal("2.5")
    assert drops[0].pct_drop >= Decimal("0.10")
    assert drops[0].saved_per_million_usd >= Decimal("0.05")


def test_ratchet_baseline_blocks_re_alert_at_same_price() -> None:
    current_pricing = {"prompt": "0.0000025", "completion": "0.000015"}
    reference = {"prompt": Decimal("2.80")}
    baseline = {"prompt": Decimal("2.50")}

    drops = detect_price_drops_from_reference(
        model_id="acme/model",
        current_pricing=current_pricing,
        reference_per_million=reference,
        baseline_per_million=baseline,
        thresholds=_thresholds(),
    )

    assert drops == []


def test_second_drop_triggers_below_ratcheted_baseline() -> None:
    current_pricing = {"prompt": "0.000002", "completion": "0.000015"}
    reference = {"prompt": Decimal("2.50")}

    drops = detect_price_drops_from_reference(
        model_id="acme/model",
        current_pricing=current_pricing,
        reference_per_million=reference,
        thresholds=_thresholds(),
    )

    assert len(drops) == 1
    assert drops[0].field == "prompt"
    assert drops[0].old_per_million_usd == Decimal("2.50")
    assert drops[0].new_per_million_usd == Decimal("2")


def test_ignores_price_increases_vs_reference() -> None:
    current_pricing = {"prompt": "0.000003", "completion": "0.000015"}
    reference = {"prompt": Decimal("2")}

    drops = detect_price_drops_from_reference(
        model_id="acme/model",
        current_pricing=current_pricing,
        reference_per_million=reference,
        thresholds=_thresholds(),
    )

    assert drops == []


def test_ignores_drop_below_pct_threshold() -> None:
    current_pricing = {"prompt": "0.0000095", "completion": "0.000015"}
    reference = {"prompt": Decimal("10")}

    drops = detect_price_drops_from_reference(
        model_id="acme/model",
        current_pricing=current_pricing,
        reference_per_million=reference,
        thresholds=_thresholds(),
    )

    assert drops == []


def test_ignores_variable_price_sentinel() -> None:
    current_pricing = {"prompt": "-1", "completion": "-1"}
    reference = {"prompt": Decimal("3"), "completion": Decimal("15")}

    drops = detect_price_drops_from_reference(
        model_id="openrouter/auto",
        current_pricing=current_pricing,
        reference_per_million=reference,
        thresholds=_thresholds(),
    )

    assert drops == []
