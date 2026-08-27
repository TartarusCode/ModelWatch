from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from modelwatch.json_output import write_model_json
from modelwatch.pricing import PriceChangeThresholds
from modelwatch.schemas import ChangeDirection, PriceChangeRecord

SETTLEMENT_BUILDS = 2
RECOVERY_BUILDS = 2
CUT_RECOVERY_FACTOR = Decimal("1.05")
HIKE_RECOVERY_FACTOR = Decimal("0.95")
SPIKE_TOLERANCE = Decimal("1.15")
DIP_TOLERANCE = Decimal("0.85")
PRICE_TOLERANCE = Decimal("0.000001")
SETTLE_AFTER = timedelta(days=7)

STATE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "snapshots"
    / "price-change-state.json"
)

FieldStatus = Literal["idle", "pending", "confirmed"]


class FieldChangeState(BaseModel):
    model_config = ConfigDict(frozen=True)

    anchor: Decimal
    status: FieldStatus = "idle"
    direction: ChangeDirection | None = None
    pending_price: Decimal | None = None
    pending_builds: int = 0
    episode_start_price: Decimal | None = None
    confirmed_price: Decimal | None = None
    confirmed_at: datetime | None = None
    recovery_builds: int = 0

    @classmethod
    def idle(cls, anchor: Decimal) -> FieldChangeState:
        return cls(anchor=anchor, status="idle")


class PriceChangeStateStore(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    models: dict[str, dict[str, FieldChangeState]] = Field(default_factory=dict)
    episodes: list[PriceChangeRecord] = Field(default_factory=list)


@dataclass(frozen=True)
class FieldUpdateResult:
    state: FieldChangeState
    confirmed: PriceChangeRecord | None
    recovered: PriceChangeRecord | None
    settled: PriceChangeRecord | None = None


def load_price_change_state() -> PriceChangeStateStore:
    if not STATE_PATH.exists():
        now = datetime.now(UTC)
        return PriceChangeStateStore(generated_at=now, models={}, episodes=[])
    import json

    payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return PriceChangeStateStore.model_validate(payload)


def save_price_change_state(store: PriceChangeStateStore) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_model_json(STATE_PATH, store)


def _prices_match(left: Decimal, right: Decimal) -> bool:
    return abs(left - right) <= PRICE_TOLERANCE


def _effective_prior_for_cut(reference: Decimal, previous: Decimal | None) -> Decimal:
    if previous is None:
        return reference
    if previous > reference * SPIKE_TOLERANCE:
        return reference
    return previous


def _effective_prior_for_hike(reference: Decimal, previous: Decimal | None) -> Decimal:
    if previous is None:
        return reference
    if previous < reference * DIP_TOLERANCE:
        return reference
    return previous


def _meets_change_thresholds(
    *,
    prior: Decimal,
    current: Decimal,
    direction: ChangeDirection,
    thresholds: PriceChangeThresholds,
) -> bool:
    if direction == "cut":
        if current >= prior:
            return False
        delta = prior - current
        if delta < thresholds.min_delta_per_million_usd:
            return False
        return (delta / prior) >= thresholds.min_pct
    if current <= prior:
        return False
    delta = current - prior
    if delta < thresholds.min_delta_per_million_usd:
        return False
    return (delta / prior) >= thresholds.min_pct


def _episode_from_confirmation(
    *,
    model_id: str,
    field: str,
    direction: ChangeDirection,
    episode_start: Decimal,
    confirmed_price: Decimal,
    detected_at: datetime,
) -> PriceChangeRecord:
    delta = confirmed_price - episode_start
    pct_change = float(delta / episode_start) if episode_start > 0 else 0.0
    return PriceChangeRecord(
        detected_at=detected_at,
        model_id=model_id,
        field=field,
        direction=direction,
        episode_start_per_million_usd=f"{episode_start:.6f}",
        old_per_million_usd=f"{episode_start:.6f}",
        new_per_million_usd=f"{confirmed_price:.6f}",
        pct_change=pct_change,
        delta_per_million_usd=f"{delta:.6f}",
        status="active",
    )


def _episode_recovered(
    episode: PriceChangeRecord,
    *,
    recovered_price: Decimal,
    recovered_at: datetime,
) -> PriceChangeRecord:
    return episode.model_copy(
        update={
            "status": "recovered",
            "recovered_at": recovered_at,
            "recovered_per_million_usd": f"{recovered_price:.6f}",
        },
    )


def _episode_settled(
    episode: PriceChangeRecord,
    *,
    settled_price: Decimal,
    settled_at: datetime,
) -> PriceChangeRecord:
    return episode.model_copy(
        update={
            "status": "settled",
            "settled_at": settled_at,
            "settled_per_million_usd": f"{settled_price:.6f}",
        },
    )


def _pending_cut_triggered(
    *,
    current: Decimal,
    previous: Decimal | None,
    anchor: Decimal,
    reference: Decimal,
    thresholds: PriceChangeThresholds,
) -> bool:
    if current >= anchor:
        return False
    if current >= reference:
        return False
    prior = _effective_prior_for_cut(reference, previous)
    return _meets_change_thresholds(
        prior=prior,
        current=current,
        direction="cut",
        thresholds=thresholds,
    )


def _pending_hike_triggered(
    *,
    current: Decimal,
    previous: Decimal | None,
    anchor: Decimal,
    reference: Decimal,
    thresholds: PriceChangeThresholds,
) -> bool:
    if current <= anchor:
        return False
    if current <= reference:
        return False
    prior = _effective_prior_for_hike(reference, previous)
    return _meets_change_thresholds(
        prior=prior,
        current=current,
        direction="hike",
        thresholds=thresholds,
    )


def update_field_change_state(
    state: FieldChangeState,
    *,
    current: Decimal,
    previous: Decimal | None,
    reference: Decimal,
    thresholds: PriceChangeThresholds,
    now: datetime,
) -> tuple[
    FieldChangeState,
    PriceChangeRecord | None,
    PriceChangeRecord | None,
    PriceChangeRecord | None,
]:
    result = _update_field_change_state(
        state,
        current=current,
        previous=previous,
        reference=reference,
        thresholds=thresholds,
        now=now,
    )
    return result.state, result.confirmed, result.recovered, result.settled


def _update_field_change_state(
    state: FieldChangeState,
    *,
    current: Decimal,
    previous: Decimal | None,
    reference: Decimal,
    thresholds: PriceChangeThresholds,
    now: datetime,
) -> FieldUpdateResult:
    if state.status == "confirmed":
        return _update_confirmed_state(
            state,
            current=current,
            previous=previous,
            reference=reference,
            thresholds=thresholds,
            now=now,
        )
    if state.status == "pending":
        return _update_pending_state(
            state,
            current=current,
            previous=previous,
            reference=reference,
            thresholds=thresholds,
            now=now,
        )
    return _update_idle_state(
        state,
        current=current,
        previous=previous,
        reference=reference,
        thresholds=thresholds,
        now=now,
    )


def _update_idle_state(
    state: FieldChangeState,
    *,
    current: Decimal,
    previous: Decimal | None,
    reference: Decimal,
    thresholds: PriceChangeThresholds,
    now: datetime,
) -> FieldUpdateResult:
    if _pending_cut_triggered(
        current=current,
        previous=previous,
        anchor=state.anchor,
        reference=reference,
        thresholds=thresholds,
    ):
        return FieldUpdateResult(
            state=state.model_copy(
                update={
                    "status": "pending",
                    "direction": "cut",
                    "pending_price": current,
                    "pending_builds": 1,
                    "episode_start_price": state.anchor,
                },
            ),
            confirmed=None,
            recovered=None,
        )

    if _pending_hike_triggered(
        current=current,
        previous=previous,
        anchor=state.anchor,
        reference=reference,
        thresholds=thresholds,
    ):
        return FieldUpdateResult(
            state=state.model_copy(
                update={
                    "status": "pending",
                    "direction": "hike",
                    "pending_price": current,
                    "pending_builds": 1,
                    "episode_start_price": state.anchor,
                },
            ),
            confirmed=None,
            recovered=None,
        )

    if not _prices_match(current, state.anchor):
        return FieldUpdateResult(
            state=state.model_copy(update={"anchor": current}),
            confirmed=None,
            recovered=None,
        )
    return FieldUpdateResult(state=state, confirmed=None, recovered=None)


def _update_pending_state(
    state: FieldChangeState,
    *,
    current: Decimal,
    previous: Decimal | None,
    reference: Decimal,
    thresholds: PriceChangeThresholds,
    now: datetime,
) -> FieldUpdateResult:
    assert state.pending_price is not None
    assert state.episode_start_price is not None
    assert state.direction is not None
    direction = state.direction

    if direction == "cut":
        if current > state.pending_price and not _prices_match(
            current, state.pending_price
        ):
            return FieldUpdateResult(
                state=FieldChangeState.idle(state.anchor),
                confirmed=None,
                recovered=None,
            )
        if current < state.pending_price and not _prices_match(
            current, state.pending_price
        ):
            if _pending_cut_triggered(
                current=current,
                previous=previous,
                anchor=state.anchor,
                reference=reference,
                thresholds=thresholds,
            ):
                return FieldUpdateResult(
                    state=state.model_copy(
                        update={
                            "pending_price": current,
                            "pending_builds": 1,
                        },
                    ),
                    confirmed=None,
                    recovered=None,
                )
            return FieldUpdateResult(
                state=FieldChangeState.idle(state.anchor),
                confirmed=None,
                recovered=None,
            )
    else:
        if current < state.pending_price and not _prices_match(
            current, state.pending_price
        ):
            return FieldUpdateResult(
                state=FieldChangeState.idle(state.anchor),
                confirmed=None,
                recovered=None,
            )
        if current > state.pending_price and not _prices_match(
            current, state.pending_price
        ):
            if _pending_hike_triggered(
                current=current,
                previous=previous,
                anchor=state.anchor,
                reference=reference,
                thresholds=thresholds,
            ):
                return FieldUpdateResult(
                    state=state.model_copy(
                        update={
                            "pending_price": current,
                            "pending_builds": 1,
                        },
                    ),
                    confirmed=None,
                    recovered=None,
                )
            return FieldUpdateResult(
                state=FieldChangeState.idle(state.anchor),
                confirmed=None,
                recovered=None,
            )

    pending_builds = state.pending_builds + 1
    if pending_builds < SETTLEMENT_BUILDS:
        return FieldUpdateResult(
            state=state.model_copy(update={"pending_builds": pending_builds}),
            confirmed=None,
            recovered=None,
        )

    confirmed_price = state.pending_price
    episode_start = state.episode_start_price
    confirmed = _episode_from_confirmation(
        model_id="",
        field="",
        direction=direction,
        episode_start=episode_start,
        confirmed_price=confirmed_price,
        detected_at=now,
    )
    return FieldUpdateResult(
        state=state.model_copy(
            update={
                "status": "confirmed",
                "anchor": confirmed_price,
                "pending_price": None,
                "pending_builds": 0,
                "confirmed_price": confirmed_price,
                "confirmed_at": now,
                "recovery_builds": 0,
            },
        ),
        confirmed=confirmed,
        recovered=None,
    )


def _update_confirmed_state(
    state: FieldChangeState,
    *,
    current: Decimal,
    previous: Decimal | None,
    reference: Decimal,
    thresholds: PriceChangeThresholds,
    now: datetime,
) -> FieldUpdateResult:
    assert state.episode_start_price is not None
    assert state.confirmed_price is not None
    assert state.direction is not None
    direction = state.direction

    if state.confirmed_at is not None and now - state.confirmed_at >= SETTLE_AFTER:
        settled = _episode_from_confirmation(
            model_id="",
            field="",
            direction=direction,
            episode_start=state.episode_start_price,
            confirmed_price=state.confirmed_price,
            detected_at=state.confirmed_at,
        ).model_copy(
            update={
                "status": "settled",
                "settled_at": now,
                "settled_per_million_usd": f"{current:.6f}",
            },
        )
        return FieldUpdateResult(
            state=FieldChangeState.idle(current),
            confirmed=None,
            recovered=None,
            settled=settled,
        )

    if direction == "cut":
        recovery_threshold = state.episode_start_price * CUT_RECOVERY_FACTOR
        recovering = current > recovery_threshold
    else:
        recovery_threshold = state.episode_start_price * HIKE_RECOVERY_FACTOR
        recovering = current < recovery_threshold

    if recovering:
        recovery_builds = state.recovery_builds + 1
        if recovery_builds >= RECOVERY_BUILDS:
            recovered = _episode_from_confirmation(
                model_id="",
                field="",
                direction=direction,
                episode_start=state.episode_start_price,
                confirmed_price=state.confirmed_price,
                detected_at=state.confirmed_at or now,
            ).model_copy(
                update={
                    "status": "recovered",
                    "recovered_at": now,
                    "recovered_per_million_usd": f"{current:.6f}",
                },
            )
            return FieldUpdateResult(
                state=FieldChangeState.idle(current),
                confirmed=None,
                recovered=recovered,
            )
        return FieldUpdateResult(
            state=state.model_copy(update={"recovery_builds": recovery_builds}),
            confirmed=None,
            recovered=None,
        )

    if direction == "cut":
        deepening = (
            current < state.confirmed_price
            and not _prices_match(current, state.confirmed_price)
            and _pending_cut_triggered(
                current=current,
                previous=previous,
                anchor=state.anchor,
                reference=reference,
                thresholds=thresholds,
            )
        )
        if deepening:
            return FieldUpdateResult(
                state=state.model_copy(
                    update={
                        "status": "pending",
                        "direction": "cut",
                        "pending_price": current,
                        "pending_builds": 1,
                        "episode_start_price": state.anchor,
                        "recovery_builds": 0,
                    },
                ),
                confirmed=None,
                recovered=None,
            )
    else:
        steepening = (
            current > state.confirmed_price
            and not _prices_match(current, state.confirmed_price)
            and _pending_hike_triggered(
                current=current,
                previous=previous,
                anchor=state.anchor,
                reference=reference,
                thresholds=thresholds,
            )
        )
        if steepening:
            return FieldUpdateResult(
                state=state.model_copy(
                    update={
                        "status": "pending",
                        "direction": "hike",
                        "pending_price": current,
                        "pending_builds": 1,
                        "episode_start_price": state.anchor,
                        "recovery_builds": 0,
                    },
                ),
                confirmed=None,
                recovered=None,
            )

    return FieldUpdateResult(
        state=state.model_copy(update={"recovery_builds": 0}),
        confirmed=None,
        recovered=None,
    )


def update_model_field_change_states(
    store: PriceChangeStateStore,
    *,
    model_id: str,
    current_per_million: dict[str, Decimal],
    previous_per_million: dict[str, Decimal] | None,
    reference_per_million: dict[str, Decimal],
    thresholds: PriceChangeThresholds,
    now: datetime,
) -> tuple[
    PriceChangeStateStore,
    list[PriceChangeRecord],
    list[PriceChangeRecord],
    list[PriceChangeRecord],
]:
    model_states = dict(store.models.get(model_id, {}))
    episodes = list(store.episodes)
    confirmed_episodes: list[PriceChangeRecord] = []
    recovered_episodes: list[PriceChangeRecord] = []
    settled_episodes: list[PriceChangeRecord] = []

    for field, reference in reference_per_million.items():
        current = current_per_million.get(field)
        if current is None or current <= 0:
            continue

        previous = previous_per_million.get(field) if previous_per_million else None
        field_state = model_states.get(field)
        if field_state is None:
            field_state = FieldChangeState.idle(current)

        new_state, confirmed, recovered, settled = update_field_change_state(
            field_state,
            current=current,
            previous=previous,
            reference=reference,
            thresholds=thresholds,
            now=now,
        )
        model_states[field] = new_state

        if confirmed is not None:
            confirmed_episode = confirmed.model_copy(
                update={"model_id": model_id, "field": field},
            )
            episodes.append(confirmed_episode)
            confirmed_episodes.append(confirmed_episode)

        if recovered is not None:
            recovered_episode = _mark_latest_episode_recovered(
                episodes,
                model_id=model_id,
                field=field,
                recovered_price=Decimal(recovered.recovered_per_million_usd or "0"),
                recovered_at=now,
            )
            if recovered_episode is not None:
                recovered_episodes.append(recovered_episode)

        if settled is not None:
            settled_episode = _mark_latest_episode_settled(
                episodes,
                model_id=model_id,
                field=field,
                settled_price=Decimal(settled.settled_per_million_usd or "0"),
                settled_at=now,
            )
            if settled_episode is not None:
                settled_episodes.append(settled_episode)

    updated_models = dict(store.models)
    if model_states:
        updated_models[model_id] = model_states
    elif model_id in updated_models:
        del updated_models[model_id]

    return (
        store.model_copy(
            update={
                "generated_at": now,
                "models": updated_models,
                "episodes": episodes,
            },
        ),
        confirmed_episodes,
        recovered_episodes,
        settled_episodes,
    )


def _mark_latest_episode_recovered(
    episodes: list[PriceChangeRecord],
    *,
    model_id: str,
    field: str,
    recovered_price: Decimal,
    recovered_at: datetime,
) -> PriceChangeRecord | None:
    for index in range(len(episodes) - 1, -1, -1):
        episode = episodes[index]
        if episode.model_id != model_id or episode.field != field:
            continue
        if episode.status != "active":
            continue
        updated = _episode_recovered(
            episode,
            recovered_price=recovered_price,
            recovered_at=recovered_at,
        )
        episodes[index] = updated
        return updated
    return None


def _mark_latest_episode_settled(
    episodes: list[PriceChangeRecord],
    *,
    model_id: str,
    field: str,
    settled_price: Decimal,
    settled_at: datetime,
) -> PriceChangeRecord | None:
    for index in range(len(episodes) - 1, -1, -1):
        episode = episodes[index]
        if episode.model_id != model_id or episode.field != field:
            continue
        if episode.status != "active":
            continue
        updated = _episode_settled(
            episode,
            settled_price=settled_price,
            settled_at=settled_at,
        )
        episodes[index] = updated
        return updated
    return None


def active_changes_from_state(store: PriceChangeStateStore) -> list[PriceChangeRecord]:
    active: list[PriceChangeRecord] = []
    for model_id, fields in store.models.items():
        for field, field_state in fields.items():
            if field_state.status != "confirmed":
                continue
            if (
                field_state.episode_start_price is None
                or field_state.confirmed_price is None
                or field_state.direction is None
            ):
                continue
            active.append(
                _episode_from_confirmation(
                    model_id=model_id,
                    field=field,
                    direction=field_state.direction,
                    episode_start=field_state.episode_start_price,
                    confirmed_price=field_state.confirmed_price,
                    detected_at=field_state.confirmed_at or store.generated_at,
                ),
            )
    return active


def close_orphaned_active_changes(
    episodes: list[PriceChangeRecord],
    models: dict[str, dict[str, FieldChangeState]],
    *,
    now: datetime,
    current_per_million_by_model: dict[str, dict[str, Decimal]] | None = None,
) -> list[PriceChangeRecord]:
    healed: list[PriceChangeRecord] = []
    for episode in episodes:
        if episode.status != "active":
            healed.append(episode)
            continue
        field_state = models.get(episode.model_id, {}).get(episode.field)
        if field_state is not None and field_state.status == "confirmed":
            healed.append(episode)
            continue
        current: Decimal | None = None
        if current_per_million_by_model is not None:
            current = current_per_million_by_model.get(episode.model_id, {}).get(
                episode.field,
            )
        healed.append(
            episode.model_copy(
                update={
                    "status": "recovered",
                    "recovered_at": now,
                    "recovered_per_million_usd": (
                        f"{current:.6f}" if current is not None else None
                    ),
                },
            ),
        )
    return healed
