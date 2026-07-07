from datetime import UTC, datetime
from decimal import Decimal

from modelwatch.price_drop_state import (
    SETTLEMENT_BUILDS,
    FieldDropState,
    PriceDropStateStore,
    update_field_drop_state,
)
from modelwatch.pricing import DEFAULT_THRESHOLDS, PriceDropThresholds


def _thresholds() -> PriceDropThresholds:
    return DEFAULT_THRESHOLDS


def _idle(anchor: str) -> FieldDropState:
    return FieldDropState.idle(Decimal(anchor))


def test_flash_dip_cancelled_before_settlement() -> None:
    state = _idle("0.574000")
    at = datetime(2026, 7, 5, 16, 1, tzinfo=UTC)

    state, confirmed, recovered = update_field_drop_state(
        state,
        current=Decimal("0.180000"),
        previous=Decimal("0.574000"),
        reference=Decimal("0.902536"),
        thresholds=_thresholds(),
        now=at,
    )

    assert confirmed is None
    assert recovered is None
    assert state.status == "pending"
    assert state.pending_price == Decimal("0.180000")

    state, confirmed, recovered = update_field_drop_state(
        state,
        current=Decimal("0.500000"),
        previous=Decimal("0.180000"),
        reference=Decimal("0.902536"),
        thresholds=_thresholds(),
        now=datetime(2026, 7, 5, 17, 1, tzinfo=UTC),
    )

    assert confirmed is None
    assert recovered is None
    assert state.status == "idle"
    assert state.pending_price is None


def test_gradual_decline_confirms_after_settlement_builds() -> None:
    state = _idle("0.930000")
    at = datetime(2026, 7, 4, 11, 31, tzinfo=UTC)

    state, confirmed, _ = update_field_drop_state(
        state,
        current=Decimal("0.820000"),
        previous=Decimal("0.930000"),
        reference=Decimal("0.936676"),
        thresholds=_thresholds(),
        now=at,
    )
    assert confirmed is None
    assert state.status == "pending"

    state, confirmed, _ = update_field_drop_state(
        state,
        current=Decimal("0.820000"),
        previous=Decimal("0.820000"),
        reference=Decimal("0.930000"),
        thresholds=_thresholds(),
        now=datetime(2026, 7, 4, 12, 1, tzinfo=UTC),
    )

    assert confirmed is not None
    assert confirmed.status == "active"
    assert confirmed.episode_start_per_million_usd == "0.930000"
    assert confirmed.new_per_million_usd == "0.820000"
    assert state.status == "confirmed"


def test_recovery_resets_anchor_after_confirmed_drop() -> None:
    state = FieldDropState(
        anchor=Decimal("0.840000"),
        status="confirmed",
        episode_start_price=Decimal("0.930000"),
        confirmed_price=Decimal("0.840000"),
        confirmed_at=datetime(2026, 7, 4, 12, 1, tzinfo=UTC),
    )

    state, confirmed, recovered = update_field_drop_state(
        state,
        current=Decimal("0.980000"),
        previous=Decimal("0.930000"),
        reference=Decimal("0.930000"),
        thresholds=_thresholds(),
        now=datetime(2026, 7, 6, 9, 1, tzinfo=UTC),
    )
    assert confirmed is None
    assert recovered is None
    assert state.recovery_builds == 1

    state, confirmed, recovered = update_field_drop_state(
        state,
        current=Decimal("0.980000"),
        previous=Decimal("0.980000"),
        reference=Decimal("0.930000"),
        thresholds=_thresholds(),
        now=datetime(2026, 7, 6, 9, 31, tzinfo=UTC),
    )

    assert confirmed is None
    assert recovered is not None
    assert recovered.status == "recovered"
    assert recovered.recovered_per_million_usd == "0.980000"
    assert state.status == "idle"
    assert state.anchor == Decimal("0.980000")


def test_new_drop_from_recovered_anchor_alerts() -> None:
    state = _idle("0.930000")
    at = datetime(2026, 7, 10, 10, 0, tzinfo=UTC)

    for build in range(SETTLEMENT_BUILDS):
        state, confirmed, _ = update_field_drop_state(
            state,
            current=Decimal("0.800000"),
            previous=Decimal("0.930000") if build == 0 else Decimal("0.800000"),
            reference=Decimal("0.930000"),
            thresholds=_thresholds(),
            now=at,
        )
        at = datetime(2026, 7, 10, 10, 30, tzinfo=UTC)

    assert confirmed is not None
    assert confirmed.new_per_million_usd == "0.800000"


def test_spike_and_return_does_not_confirm() -> None:
    state = _idle("3.000000")

    state, confirmed, _ = update_field_drop_state(
        state,
        current=Decimal("3.000000"),
        previous=Decimal("5.000000"),
        reference=Decimal("3.000000"),
        thresholds=_thresholds(),
        now=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
    )

    assert confirmed is None
    assert state.status == "idle"


def test_store_round_trip() -> None:
    at = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    store = PriceDropStateStore(
        generated_at=at,
        models={"acme/model": {"prompt": _idle("1.000000")}},
        episodes=[],
    )
    payload = store.model_dump_json()
    loaded = PriceDropStateStore.model_validate_json(payload)
    assert loaded.models["acme/model"]["prompt"].anchor == Decimal("1.000000")
