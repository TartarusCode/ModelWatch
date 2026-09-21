from decimal import Decimal

import pytest

from modelwatch.pricing import (
    TIER_OFFPEAK,
    PriceChangeThresholds,
    per_million_usd,
    pricing_fields_to_compare,
    split_track_key,
    tier_label,
    track_key,
)


def _thresholds() -> PriceChangeThresholds:
    return PriceChangeThresholds(
        min_pct=Decimal("0.10"),
        min_delta_per_million_usd=Decimal("0.05"),
    )


def test_per_million_usd_converts_per_token_string() -> None:
    assert per_million_usd("0.000008") == Decimal("8")


def test_ignores_variable_price_sentinel() -> None:
    with pytest.raises(ValueError, match="not a displayable price"):
        per_million_usd("-1")


def test_compares_optional_pricing_fields_when_present() -> None:
    fields = pricing_fields_to_compare(
        {"prompt": "1", "completion": "2", "image": "3"},
        {"prompt": "1", "completion": "2"},
    )
    assert fields == ("prompt", "completion")


def test_track_keys_round_trip_for_both_tiers() -> None:
    assert track_key("prompt", None) == "prompt"
    assert track_key("prompt", TIER_OFFPEAK) == "prompt_offpeak"
    assert split_track_key("prompt") == ("prompt", None)
    assert split_track_key("prompt_offpeak") == ("prompt", TIER_OFFPEAK)
    assert split_track_key("input_cache_read_offpeak") == (
        "input_cache_read",
        TIER_OFFPEAK,
    )


def test_tier_labels() -> None:
    assert tier_label(None) is None
    assert tier_label(TIER_OFFPEAK) == "off-peak"
    assert tier_label("something-else") == "something-else"
