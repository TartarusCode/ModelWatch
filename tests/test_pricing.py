from decimal import Decimal

import pytest

from modelwatch.pricing import (
    PriceDropThresholds,
    per_million_usd,
    pricing_fields_to_compare,
)


def _thresholds() -> PriceDropThresholds:
    return PriceDropThresholds(
        min_pct=Decimal("0.10"),
        min_saved_per_million_usd=Decimal("0.05"),
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
