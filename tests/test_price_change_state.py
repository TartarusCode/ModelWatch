from datetime import UTC, datetime, timedelta
from decimal import Decimal

from modelwatch.price_change_state import (
    SETTLEMENT_BUILDS,
    FieldChangeState,
    PriceChangeStateStore,
    PriceTrack,
    active_changes_from_state,
    close_orphaned_active_changes,
    rebase_model_field_change_states,
    update_field_change_state,
    update_model_field_change_states,
)
from modelwatch.pricing import DEFAULT_THRESHOLDS, PriceChangeThresholds
from modelwatch.schemas import PriceChangeRecord


def _thresholds() -> PriceChangeThresholds:
    return DEFAULT_THRESHOLDS


def _idle(anchor: str) -> FieldChangeState:
    return FieldChangeState.idle(Decimal(anchor))


def test_flash_dip_cancelled_before_settlement() -> None:
    state = _idle("0.574000")
    at = datetime(2026, 7, 5, 16, 1, tzinfo=UTC)

    state, confirmed, recovered, settled = update_field_change_state(
        state,
        current=Decimal("0.180000"),
        previous=Decimal("0.574000"),
        reference=Decimal("0.902536"),
        thresholds=_thresholds(),
        now=at,
    )

    assert confirmed is None
    assert recovered is None
    assert settled is None
    assert state.status == "pending"
    assert state.direction == "cut"
    assert state.pending_price == Decimal("0.180000")

    state, confirmed, recovered, settled = update_field_change_state(
        state,
        current=Decimal("0.500000"),
        previous=Decimal("0.180000"),
        reference=Decimal("0.902536"),
        thresholds=_thresholds(),
        now=datetime(2026, 7, 5, 17, 1, tzinfo=UTC),
    )

    assert confirmed is None
    assert recovered is None
    assert settled is None
    assert state.status == "idle"
    assert state.pending_price is None
    assert state.direction is None


def test_flash_hike_cancelled_before_settlement() -> None:
    state = _idle("1.000000")
    at = datetime(2026, 7, 5, 16, 1, tzinfo=UTC)

    state, confirmed, recovered, settled = update_field_change_state(
        state,
        current=Decimal("1.500000"),
        previous=Decimal("1.000000"),
        reference=Decimal("1.000000"),
        thresholds=_thresholds(),
        now=at,
    )

    assert confirmed is None
    assert recovered is None
    assert settled is None
    assert state.status == "pending"
    assert state.direction == "hike"
    assert state.pending_price == Decimal("1.500000")

    state, confirmed, recovered, settled = update_field_change_state(
        state,
        current=Decimal("1.100000"),
        previous=Decimal("1.500000"),
        reference=Decimal("1.000000"),
        thresholds=_thresholds(),
        now=datetime(2026, 7, 5, 17, 1, tzinfo=UTC),
    )

    assert confirmed is None
    assert recovered is None
    assert settled is None
    assert state.status == "idle"
    assert state.pending_price is None


def test_gradual_decline_confirms_after_settlement_builds() -> None:
    state = _idle("0.930000")
    at = datetime(2026, 7, 4, 11, 31, tzinfo=UTC)

    state, confirmed, _, _ = update_field_change_state(
        state,
        current=Decimal("0.820000"),
        previous=Decimal("0.930000"),
        reference=Decimal("0.936676"),
        thresholds=_thresholds(),
        now=at,
    )
    assert confirmed is None
    assert state.status == "pending"
    assert state.direction == "cut"

    state, confirmed, _, _ = update_field_change_state(
        state,
        current=Decimal("0.820000"),
        previous=Decimal("0.820000"),
        reference=Decimal("0.930000"),
        thresholds=_thresholds(),
        now=datetime(2026, 7, 4, 12, 1, tzinfo=UTC),
    )

    assert confirmed is not None
    assert confirmed.status == "active"
    assert confirmed.direction == "cut"
    assert confirmed.episode_start_per_million_usd == "0.930000"
    assert confirmed.new_per_million_usd == "0.820000"
    assert confirmed.pct_change < 0
    assert Decimal(confirmed.delta_per_million_usd) < 0
    assert state.status == "confirmed"


def test_gradual_hike_confirms_after_settlement_builds() -> None:
    state = _idle("1.000000")
    at = datetime(2026, 7, 4, 11, 31, tzinfo=UTC)

    state, confirmed, _, _ = update_field_change_state(
        state,
        current=Decimal("1.200000"),
        previous=Decimal("1.000000"),
        reference=Decimal("1.000000"),
        thresholds=_thresholds(),
        now=at,
    )
    assert confirmed is None
    assert state.status == "pending"
    assert state.direction == "hike"

    state, confirmed, _, _ = update_field_change_state(
        state,
        current=Decimal("1.200000"),
        previous=Decimal("1.200000"),
        reference=Decimal("1.000000"),
        thresholds=_thresholds(),
        now=datetime(2026, 7, 4, 12, 1, tzinfo=UTC),
    )

    assert confirmed is not None
    assert confirmed.status == "active"
    assert confirmed.direction == "hike"
    assert confirmed.episode_start_per_million_usd == "1.000000"
    assert confirmed.new_per_million_usd == "1.200000"
    assert confirmed.pct_change > 0
    assert Decimal(confirmed.delta_per_million_usd) > 0
    assert state.status == "confirmed"


def test_recovery_resets_anchor_after_confirmed_cut() -> None:
    state = FieldChangeState(
        anchor=Decimal("0.840000"),
        status="confirmed",
        direction="cut",
        episode_start_price=Decimal("0.930000"),
        confirmed_price=Decimal("0.840000"),
        confirmed_at=datetime(2026, 7, 4, 12, 1, tzinfo=UTC),
    )

    state, confirmed, recovered, settled = update_field_change_state(
        state,
        current=Decimal("0.980000"),
        previous=Decimal("0.930000"),
        reference=Decimal("0.930000"),
        thresholds=_thresholds(),
        now=datetime(2026, 7, 6, 9, 1, tzinfo=UTC),
    )
    assert confirmed is None
    assert recovered is None
    assert settled is None
    assert state.recovery_builds == 1

    state, confirmed, recovered, settled = update_field_change_state(
        state,
        current=Decimal("0.980000"),
        previous=Decimal("0.980000"),
        reference=Decimal("0.930000"),
        thresholds=_thresholds(),
        now=datetime(2026, 7, 6, 9, 31, tzinfo=UTC),
    )

    assert confirmed is None
    assert recovered is not None
    assert settled is None
    assert recovered.status == "recovered"
    assert recovered.direction == "cut"
    assert recovered.recovered_per_million_usd == "0.980000"
    assert state.status == "idle"
    assert state.anchor == Decimal("0.980000")


def test_recovery_resets_anchor_after_confirmed_hike() -> None:
    state = FieldChangeState(
        anchor=Decimal("1.200000"),
        status="confirmed",
        direction="hike",
        episode_start_price=Decimal("1.000000"),
        confirmed_price=Decimal("1.200000"),
        confirmed_at=datetime(2026, 7, 4, 12, 1, tzinfo=UTC),
    )

    state, confirmed, recovered, settled = update_field_change_state(
        state,
        current=Decimal("0.900000"),
        previous=Decimal("1.200000"),
        reference=Decimal("1.000000"),
        thresholds=_thresholds(),
        now=datetime(2026, 7, 6, 9, 1, tzinfo=UTC),
    )
    assert confirmed is None
    assert recovered is None
    assert settled is None
    assert state.recovery_builds == 1

    state, confirmed, recovered, settled = update_field_change_state(
        state,
        current=Decimal("0.900000"),
        previous=Decimal("0.900000"),
        reference=Decimal("1.000000"),
        thresholds=_thresholds(),
        now=datetime(2026, 7, 6, 9, 31, tzinfo=UTC),
    )

    assert confirmed is None
    assert recovered is not None
    assert settled is None
    assert recovered.status == "recovered"
    assert recovered.direction == "hike"
    assert recovered.recovered_per_million_usd == "0.900000"
    assert state.status == "idle"
    assert state.anchor == Decimal("0.900000")


def test_confirmed_cut_settles_after_seven_days() -> None:
    confirmed_at = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    state = FieldChangeState(
        anchor=Decimal("0.840000"),
        status="confirmed",
        direction="cut",
        episode_start_price=Decimal("0.930000"),
        confirmed_price=Decimal("0.840000"),
        confirmed_at=confirmed_at,
    )
    now = confirmed_at + timedelta(days=8)
    active_episode = PriceChangeRecord(
        detected_at=confirmed_at,
        model_id="acme/model",
        field="prompt",
        direction="cut",
        episode_start_per_million_usd="0.930000",
        old_per_million_usd="0.930000",
        new_per_million_usd="0.840000",
        pct_change=-0.0967741935483871,
        delta_per_million_usd="-0.090000",
        status="active",
    )
    store = PriceChangeStateStore(
        generated_at=confirmed_at,
        models={"acme/model": {"prompt": state}},
        episodes=[active_episode],
    )

    store, _, _, settled = update_model_field_change_states(
        store,
        model_id="acme/model",
        tracks=[
            PriceTrack(
                field="prompt",
                current=Decimal("0.840000"),
                previous=Decimal("0.840000"),
                reference=Decimal("0.900000"),
            ),
        ],
        thresholds=_thresholds(),
        now=now,
    )

    assert len(settled) == 1
    assert settled[0].status == "settled"
    assert settled[0].direction == "cut"
    assert settled[0].settled_at == now
    assert settled[0].settled_per_million_usd == "0.840000"
    assert store.models["acme/model"]["prompt"].status == "idle"
    assert store.models["acme/model"]["prompt"].anchor == Decimal("0.840000")
    assert store.episodes[0].status == "settled"


def test_confirmed_hike_settles_after_seven_days() -> None:
    confirmed_at = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    state = FieldChangeState(
        anchor=Decimal("1.200000"),
        status="confirmed",
        direction="hike",
        episode_start_price=Decimal("1.000000"),
        confirmed_price=Decimal("1.200000"),
        confirmed_at=confirmed_at,
    )
    now = confirmed_at + timedelta(days=8)
    active_episode = PriceChangeRecord(
        detected_at=confirmed_at,
        model_id="acme/model",
        field="prompt",
        direction="hike",
        episode_start_per_million_usd="1.000000",
        old_per_million_usd="1.000000",
        new_per_million_usd="1.200000",
        pct_change=0.2,
        delta_per_million_usd="0.200000",
        status="active",
    )
    store = PriceChangeStateStore(
        generated_at=confirmed_at,
        models={"acme/model": {"prompt": state}},
        episodes=[active_episode],
    )

    store, _, _, settled = update_model_field_change_states(
        store,
        model_id="acme/model",
        tracks=[
            PriceTrack(
                field="prompt",
                current=Decimal("1.200000"),
                previous=Decimal("1.200000"),
                reference=Decimal("1.000000"),
            ),
        ],
        thresholds=_thresholds(),
        now=now,
    )

    assert len(settled) == 1
    assert settled[0].status == "settled"
    assert settled[0].direction == "hike"
    assert store.models["acme/model"]["prompt"].status == "idle"
    assert store.models["acme/model"]["prompt"].anchor == Decimal("1.200000")


def test_confirmed_change_does_not_settle_before_seven_days() -> None:
    confirmed_at = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    state = FieldChangeState(
        anchor=Decimal("0.840000"),
        status="confirmed",
        direction="cut",
        episode_start_price=Decimal("0.930000"),
        confirmed_price=Decimal("0.840000"),
        confirmed_at=confirmed_at,
    )

    state, confirmed, recovered, settled = update_field_change_state(
        state,
        current=Decimal("0.840000"),
        previous=Decimal("0.840000"),
        reference=Decimal("0.900000"),
        thresholds=_thresholds(),
        now=confirmed_at + timedelta(days=6),
    )

    assert confirmed is None
    assert recovered is None
    assert settled is None
    assert state.status == "confirmed"


def test_new_cut_from_recovered_anchor_alerts() -> None:
    state = _idle("0.930000")
    at = datetime(2026, 7, 10, 10, 0, tzinfo=UTC)

    for build in range(SETTLEMENT_BUILDS):
        state, confirmed, _, _ = update_field_change_state(
            state,
            current=Decimal("0.800000"),
            previous=Decimal("0.930000") if build == 0 else Decimal("0.800000"),
            reference=Decimal("0.930000"),
            thresholds=_thresholds(),
            now=at,
        )
        at = datetime(2026, 7, 10, 10, 30, tzinfo=UTC)

    assert confirmed is not None
    assert confirmed.direction == "cut"
    assert confirmed.new_per_million_usd == "0.800000"


def test_spike_and_return_does_not_confirm_cut() -> None:
    state = _idle("3.000000")

    state, confirmed, _, _ = update_field_change_state(
        state,
        current=Decimal("3.000000"),
        previous=Decimal("5.000000"),
        reference=Decimal("3.000000"),
        thresholds=_thresholds(),
        now=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
    )

    assert confirmed is None
    assert state.status == "idle"


def test_dip_and_return_does_not_confirm_hike() -> None:
    state = _idle("3.000000")

    state, confirmed, _, _ = update_field_change_state(
        state,
        current=Decimal("3.000000"),
        previous=Decimal("2.000000"),
        reference=Decimal("3.000000"),
        thresholds=_thresholds(),
        now=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
    )

    assert confirmed is None
    assert state.status == "idle"


def test_active_changes_from_state_reflects_confirmed_fields_only() -> None:
    at = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    confirmed_state = FieldChangeState(
        anchor=Decimal("0.820000"),
        status="confirmed",
        direction="cut",
        episode_start_price=Decimal("0.930000"),
        confirmed_price=Decimal("0.820000"),
        confirmed_at=at,
    )
    stale_episode = PriceChangeRecord(
        detected_at=datetime(2026, 6, 18, 20, 39, tzinfo=UTC),
        model_id="z-ai/glm-5.2",
        field="prompt",
        direction="cut",
        episode_start_per_million_usd="1.400000",
        old_per_million_usd="1.400000",
        new_per_million_usd="1.200000",
        pct_change=-0.14285714285714285,
        delta_per_million_usd="-0.200000",
        status="active",
    )
    store = PriceChangeStateStore(
        generated_at=at,
        models={
            "z-ai/glm-5.2": {
                "prompt": confirmed_state,
                "completion": _idle("3.000000"),
            },
        },
        episodes=[stale_episode],
    )

    active = active_changes_from_state(store)

    assert len(active) == 1
    assert active[0].model_id == "z-ai/glm-5.2"
    assert active[0].field == "prompt"
    assert active[0].direction == "cut"
    assert active[0].new_per_million_usd == "0.820000"
    assert active[0].episode_start_per_million_usd == "0.930000"


def test_close_orphaned_active_changes_recovers_unmatched_active_rows() -> None:
    now = datetime(2026, 7, 8, 12, 0, tzinfo=UTC)
    stale_episode = PriceChangeRecord(
        detected_at=datetime(2026, 6, 18, 20, 39, tzinfo=UTC),
        model_id="z-ai/glm-5.2",
        field="prompt",
        direction="cut",
        episode_start_per_million_usd="1.400000",
        old_per_million_usd="1.400000",
        new_per_million_usd="1.200000",
        pct_change=-0.14285714285714285,
        delta_per_million_usd="-0.200000",
        status="active",
    )
    models = {
        "z-ai/glm-5.2": {
            "prompt": _idle("0.930000"),
        },
    }

    healed = close_orphaned_active_changes(
        [stale_episode],
        models,
        now=now,
        current_per_million_by_model={
            "z-ai/glm-5.2": {"prompt": Decimal("0.930000")},
        },
    )

    assert len(healed) == 1
    assert healed[0].status == "recovered"
    assert healed[0].recovered_at == now
    assert healed[0].recovered_per_million_usd == "0.930000"


def test_rebase_reanchors_without_emitting_episodes() -> None:
    now = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
    store = PriceChangeStateStore(
        generated_at=now,
        models={
            "deepseek/deepseek-v4.1-flash": {
                "prompt": _idle("0.150000"),
                "completion": _idle("0.600000"),
            },
        },
        episodes=[],
    )

    rebased = rebase_model_field_change_states(
        store,
        model_id="deepseek/deepseek-v4.1-flash",
        current_per_million={
            "prompt": Decimal("0.300000"),
            "completion": Decimal("1.200000"),
        },
        now=now,
    )

    prompt_state = rebased.models["deepseek/deepseek-v4.1-flash"]["prompt"]
    assert prompt_state.anchor == Decimal("0.300000")
    assert prompt_state.status == "idle"
    assert prompt_state.pending_price is None
    assert rebased.episodes == []


def test_rebase_drops_in_flight_pending_state() -> None:
    now = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
    pending = FieldChangeState(
        anchor=Decimal("0.150000"),
        status="pending",
        direction="hike",
        pending_price=Decimal("0.300000"),
        pending_builds=1,
        episode_start_price=Decimal("0.150000"),
    )
    store = PriceChangeStateStore(
        generated_at=now,
        models={"acme/model": {"prompt": pending}},
        episodes=[],
    )

    rebased = rebase_model_field_change_states(
        store,
        model_id="acme/model",
        current_per_million={"prompt": Decimal("0.300000")},
        now=now,
    )

    state = rebased.models["acme/model"]["prompt"]
    assert state.status == "idle"
    assert state.anchor == Decimal("0.300000")


def test_rebase_keeps_untouched_fields_and_other_models() -> None:
    now = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
    store = PriceChangeStateStore(
        generated_at=now,
        models={
            "acme/model": {"prompt": _idle("1.000000")},
            "other/model": {"prompt": _idle("2.000000")},
        },
        episodes=[],
    )

    rebased = rebase_model_field_change_states(
        store,
        model_id="acme/model",
        current_per_million={"completion": Decimal("3.000000")},
        now=now,
    )

    assert rebased.models["acme/model"]["prompt"].anchor == Decimal("1.000000")
    assert rebased.models["acme/model"]["completion"].anchor == Decimal("3.000000")
    assert rebased.models["other/model"]["prompt"].anchor == Decimal("2.000000")


def test_rebase_ignores_non_positive_prices() -> None:
    now = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
    store = PriceChangeStateStore(
        generated_at=now,
        models={"acme/model": {"prompt": _idle("1.000000")}},
        episodes=[],
    )

    rebased = rebase_model_field_change_states(
        store,
        model_id="acme/model",
        current_per_million={"prompt": Decimal("0")},
        now=now,
    )

    assert rebased.models["acme/model"]["prompt"].anchor == Decimal("1.000000")


def test_off_peak_track_alerts_without_a_moving_average() -> None:
    """Discount tracks have no history, so they run without the MA gate."""
    at = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
    state = _idle("0.150000")

    state, confirmed, _, _ = update_field_change_state(
        state,
        current=Decimal("0.100000"),
        previous=Decimal("0.150000"),
        reference=None,
        thresholds=_thresholds(),
        now=at,
    )
    assert confirmed is None
    assert state.status == "pending"

    state, confirmed, _, _ = update_field_change_state(
        state,
        current=Decimal("0.100000"),
        previous=Decimal("0.150000"),
        reference=None,
        thresholds=_thresholds(),
        now=at + timedelta(hours=1),
    )
    assert confirmed is not None
    assert confirmed.direction == "cut"
    assert confirmed.episode_start_per_million_usd == "0.150000"
    assert confirmed.new_per_million_usd == "0.100000"


def test_active_changes_carry_the_track_tier() -> None:
    now = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)

    def confirmed_cut(start: str, current: str) -> FieldChangeState:
        return FieldChangeState(
            anchor=Decimal(current),
            status="confirmed",
            direction="cut",
            episode_start_price=Decimal(start),
            confirmed_price=Decimal(current),
            confirmed_at=now,
        )

    store = PriceChangeStateStore(
        generated_at=now,
        models={
            "deepseek/deepseek-v4.1-flash": {
                "prompt": confirmed_cut("0.300000", "0.240000"),
                "prompt_offpeak": confirmed_cut("0.150000", "0.100000"),
            },
        },
        episodes=[],
    )

    active = active_changes_from_state(store)

    assert {(change.field, change.tier) for change in active} == {
        ("prompt", None),
        ("prompt", "offpeak"),
    }


def test_orphaned_off_peak_episode_heals_against_its_own_track() -> None:
    now = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
    episode = PriceChangeRecord(
        detected_at=now,
        model_id="acme/model",
        field="prompt",
        direction="cut",
        episode_start_per_million_usd="0.150000",
        old_per_million_usd="0.150000",
        new_per_million_usd="0.100000",
        pct_change=-0.333333,
        delta_per_million_usd="-0.050000",
        status="active",
        tier="offpeak",
    )
    models = {
        "acme/model": {
            "prompt": FieldChangeState(
                anchor=Decimal("0.300000"),
                status="confirmed",
                direction="cut",
                episode_start_price=Decimal("0.300000"),
                confirmed_price=Decimal("0.240000"),
                confirmed_at=now,
            ),
        },
    }

    healed = close_orphaned_active_changes(
        [episode],
        models,
        now=now,
        current_per_million_by_model={
            "acme/model": {
                "prompt": Decimal("0.300000"),
                "prompt_offpeak": Decimal("0.100000"),
            },
        },
    )

    assert healed[0].status == "recovered"
    assert healed[0].recovered_per_million_usd == "0.100000"


def test_discount_track_is_dropped_when_the_discount_disappears() -> None:
    now = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
    store = PriceChangeStateStore(
        generated_at=now,
        models={
            "acme/model": {
                "prompt": _idle("0.300000"),
                "prompt_offpeak": _idle("0.150000"),
            },
        },
        episodes=[],
    )

    updated, _, _, _ = update_model_field_change_states(
        store,
        model_id="acme/model",
        tracks=[
            PriceTrack(
                field="prompt",
                current=Decimal("0.300000"),
                reference=Decimal("0.300000"),
            ),
        ],
        thresholds=_thresholds(),
        now=now,
    )

    assert "prompt" in updated.models["acme/model"]
    assert "prompt_offpeak" not in updated.models["acme/model"]


def test_store_round_trip() -> None:
    at = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)
    store = PriceChangeStateStore(
        generated_at=at,
        models={"acme/model": {"prompt": _idle("1.000000")}},
        episodes=[],
    )
    payload = store.model_dump_json()
    loaded = PriceChangeStateStore.model_validate_json(payload)
    assert loaded.models["acme/model"]["prompt"].anchor == Decimal("1.000000")
