from decimal import Decimal

from modelwatch.pricing_schedule import (
    per_million_or_none,
    pricing_schedule_from_raw,
    scheduled_rates_per_million,
    standard_per_million,
    standard_pricing,
    window_label,
)
from modelwatch.schemas import (
    ModelArchitecture,
    ModelPricing,
    ModelSnapshot,
    TopProviderInfo,
)

# Trimmed from the live OpenRouter models API for deepseek/deepseek-v4.1-flash:
# off-peak $0.15/$0.60, weekday peaks 01:00-04:00 and 06:00-10:00 UTC at
# $0.30/$1.20.
DEEPSEEK_PRICING: dict[str, object] = {
    "prompt": "0.00000015",
    "completion": "0.0000006",
    "input_cache_read": "0.000000003",
    "overrides": [
        {
            "utc_days": ["saturday", "sunday"],
            "prompt": "0.00000015",
            "completion": "0.0000006",
            "input_cache_read": "0.000000003",
        },
        {
            "utc_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "utc_start": 100,
            "utc_end": 400,
            "prompt": "0.0000003",
            "completion": "0.0000012",
            "input_cache_read": "0.000000006",
        },
        {
            "utc_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "utc_start": 1000,
            "utc_end": 0,
            "prompt": "0.00000015",
            "completion": "0.0000006",
            "input_cache_read": "0.000000003",
        },
    ],
}


def _snapshot(
    pricing: ModelPricing,
    *,
    model_id: str = "acme/scheduled",
    schedule_raw: object | None = None,
) -> ModelSnapshot:
    schedule = pricing_schedule_from_raw(
        schedule_raw
        if schedule_raw is not None
        else {"prompt": pricing.prompt, "completion": pricing.completion},
    )
    return ModelSnapshot(
        id=model_id,
        canonical_slug=model_id,
        name="Scheduled",
        created=1,
        architecture=ModelArchitecture(
            input_modalities=["text"],
            output_modalities=["text"],
        ),
        pricing=pricing,
        pricing_schedule=schedule,
        top_provider=TopProviderInfo(is_moderated=False),
        supported_parameters=["temperature"],
    )


def test_schedule_without_overrides_is_none() -> None:
    assert pricing_schedule_from_raw({"prompt": "0.000001"}) is None
    assert pricing_schedule_from_raw({"prompt": "0.000001", "overrides": []}) is None
    assert pricing_schedule_from_raw("not-a-dict") is None


def test_schedule_ignores_overrides_without_usable_rates() -> None:
    raw = {"prompt": "0.000001", "overrides": [{"utc_start": 0, "utc_end": 60}]}
    assert pricing_schedule_from_raw(raw) is None


def test_context_length_tiers_are_not_a_schedule() -> None:
    """min_prompt_tokens entries are long-context tiers, not time windows."""
    raw = {
        "prompt": "0.000003",
        "completion": "0.000015",
        "overrides": [
            {
                "min_prompt_tokens": 200000,
                "prompt": "0.000006",
                "completion": "0.0000225",
            },
        ],
    }

    assert pricing_schedule_from_raw(raw) is None


def test_schedule_keeps_time_windows_and_drops_tier_entries() -> None:
    raw = {
        "prompt": "0.000001",
        "overrides": [
            {"min_prompt_tokens": 32000, "prompt": "0.000002"},
            {"utc_start": 1600, "utc_end": 0, "prompt": "0.0000005"},
        ],
    }

    schedule = pricing_schedule_from_raw(raw)

    assert schedule is not None
    assert len(schedule.windows) == 1
    assert schedule.standard["prompt"] == "0.000001"
    assert schedule.minimum["prompt"] == "0.0000005"


def test_schedule_standard_is_the_peak_rate_and_minimum_the_discount() -> None:
    schedule = pricing_schedule_from_raw(DEEPSEEK_PRICING)

    assert schedule is not None
    assert schedule.standard["prompt"] == "0.0000003"
    assert schedule.standard["completion"] == "0.0000012"
    assert schedule.minimum["prompt"] == "0.00000015"
    assert schedule.minimum["completion"] == "0.0000006"


def test_schedule_keeps_every_distinct_rate() -> None:
    schedule = pricing_schedule_from_raw(DEEPSEEK_PRICING)

    assert schedule is not None
    rates = scheduled_rates_per_million(schedule)

    assert rates["prompt"] == (Decimal("0.15"), Decimal("0.3"))
    assert rates["completion"] == (Decimal("0.6"), Decimal("1.2"))


def test_schedule_includes_the_top_level_rate_when_no_window_uses_it() -> None:
    """The model's own price counts even if every window quotes something else."""
    schedule = pricing_schedule_from_raw(
        {
            "prompt": "0.000002",
            "completion": "0.000004",
            "overrides": [
                {
                    "utc_days": ["saturday", "sunday"],
                    "prompt": "0.000001",
                    "completion": "0.000002",
                },
            ],
        },
    )

    assert schedule is not None
    assert schedule.rates["prompt"] == ["0.000001", "0.000002"]
    assert schedule.standard["prompt"] == "0.000002"
    assert schedule.minimum["prompt"] == "0.000001"


def test_schedule_dedupes_rates_written_differently() -> None:
    schedule = pricing_schedule_from_raw(
        {
            "prompt": "0.000001",
            "overrides": [{"utc_start": 0, "utc_end": 100, "prompt": "1e-6"}],
        },
    )

    assert schedule is not None
    assert schedule.rates["prompt"] == ["0.000001"]
    assert schedule.standard["prompt"] == schedule.minimum["prompt"]


def test_window_labels_describe_days_and_times() -> None:
    assert window_label(None, None, None) == "Every day all day UTC"
    assert (
        window_label(["monday", "tuesday", "wednesday", "thursday", "friday"], 100, 400)
        == "Mon–Fri 01:00–04:00 UTC"
    )
    assert window_label(["saturday", "sunday"], None, None) == "Sat–Sun all day UTC"
    assert (
        window_label(["monday", "tuesday", "wednesday", "thursday", "friday"], 1000, 0)
        == "Mon–Fri 10:00–24:00 UTC"
    )


def test_standard_per_million_uses_peak_rate_for_scheduled_fields() -> None:
    snapshot = _snapshot(
        ModelPricing(prompt="0.00000015", completion="0.0000006"),
        schedule_raw=DEEPSEEK_PRICING,
    )

    prices = standard_per_million(snapshot)

    # Off-peak window active right now, but the standard rate is the peak rate.
    assert prices["prompt"] == Decimal("0.3")
    assert prices["completion"] == Decimal("1.2")


def test_standard_per_million_falls_back_to_current_price_without_schedule() -> None:
    snapshot = _snapshot(ModelPricing(prompt="0.000001", completion="0.000002"))

    prices = standard_per_million(snapshot)

    assert prices["prompt"] == Decimal("1")
    assert prices["completion"] == Decimal("2")


def test_standard_per_million_keeps_unscheduled_fields() -> None:
    snapshot = _snapshot(
        ModelPricing(
            prompt="0.00000015",
            completion="0.0000006",
            web_search="0.005",
        ),
        schedule_raw=DEEPSEEK_PRICING,
    )

    prices = standard_per_million(snapshot)

    assert prices["web_search"] == Decimal("5000")


def test_standard_pricing_rewrites_scheduled_fields_only() -> None:
    snapshot = _snapshot(
        ModelPricing(
            prompt="0.00000015",
            completion="0.0000006",
            web_search="0.005",
        ),
        schedule_raw=DEEPSEEK_PRICING,
    )

    pricing = standard_pricing(snapshot)

    assert pricing.prompt == "0.0000003"
    assert pricing.completion == "0.0000012"
    assert pricing.web_search == "0.005"


def test_standard_pricing_is_identity_without_schedule() -> None:
    snapshot = _snapshot(ModelPricing(prompt="0.000001", completion="0.000002"))

    assert standard_pricing(snapshot) == snapshot.pricing


def test_per_million_or_none_rejects_variable_price() -> None:
    assert per_million_or_none("-1") is None
    assert per_million_or_none(None) is None
    assert per_million_or_none("0.000001") == Decimal("1")
