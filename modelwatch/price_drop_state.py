from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from modelwatch.json_output import write_model_json
from modelwatch.pricing import PriceDropThresholds
from modelwatch.schemas import PriceDropRecord

SETTLEMENT_BUILDS = 2
RECOVERY_BUILDS = 2
RECOVERY_FACTOR = Decimal("1.05")
SPIKE_TOLERANCE = Decimal("1.15")
PRICE_TOLERANCE = Decimal("0.000001")

STATE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "snapshots"
    / "price-drop-state.json"
)

FieldStatus = Literal["idle", "pending", "confirmed"]


class FieldDropState(BaseModel):
    model_config = ConfigDict(frozen=True)

    anchor: Decimal
    status: FieldStatus = "idle"
    pending_price: Decimal | None = None
    pending_builds: int = 0
    episode_start_price: Decimal | None = None
    confirmed_price: Decimal | None = None
    confirmed_at: datetime | None = None
    recovery_builds: int = 0

    @classmethod
    def idle(cls, anchor: Decimal) -> FieldDropState:
        return cls(anchor=anchor, status="idle")


class PriceDropStateStore(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    models: dict[str, dict[str, FieldDropState]] = Field(default_factory=dict)
    episodes: list[PriceDropRecord] = Field(default_factory=list)


@dataclass(frozen=True)
class FieldUpdateResult:
    state: FieldDropState
    confirmed: PriceDropRecord | None
    recovered: PriceDropRecord | None


def load_price_drop_state() -> PriceDropStateStore:
    if not STATE_PATH.exists():
        now = datetime.now(UTC)
        return PriceDropStateStore(generated_at=now, models={}, episodes=[])
    import json

    payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return PriceDropStateStore.model_validate(payload)


def save_price_drop_state(store: PriceDropStateStore) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_model_json(STATE_PATH, store)


def _prices_match(left: Decimal, right: Decimal) -> bool:
    return abs(left - right) <= PRICE_TOLERANCE


def _effective_prior(reference: Decimal, previous: Decimal | None) -> Decimal:
    if previous is None:
        return reference
    if previous > reference * SPIKE_TOLERANCE:
        return reference
    return previous


def _meets_drop_thresholds(
    *,
    prior: Decimal,
    current: Decimal,
    thresholds: PriceDropThresholds,
) -> bool:
    if current >= prior:
        return False
    saved = prior - current
    if saved < thresholds.min_saved_per_million_usd:
        return False
    pct_drop = saved / prior
    return pct_drop >= thresholds.min_pct


def _episode_from_confirmation(
    *,
    model_id: str,
    field: str,
    episode_start: Decimal,
    confirmed_price: Decimal,
    detected_at: datetime,
) -> PriceDropRecord:
    saved = episode_start - confirmed_price
    pct_drop = float(saved / episode_start) if episode_start > 0 else 0.0
    return PriceDropRecord(
        detected_at=detected_at,
        model_id=model_id,
        field=field,
        episode_start_per_million_usd=f"{episode_start:.6f}",
        old_per_million_usd=f"{episode_start:.6f}",
        new_per_million_usd=f"{confirmed_price:.6f}",
        pct_drop=pct_drop,
        saved_per_million_usd=f"{saved:.6f}",
        status="active",
    )


def _episode_recovered(
    episode: PriceDropRecord,
    *,
    recovered_price: Decimal,
    recovered_at: datetime,
) -> PriceDropRecord:
    return episode.model_copy(
        update={
            "status": "recovered",
            "recovered_at": recovered_at,
            "recovered_per_million_usd": f"{recovered_price:.6f}",
        },
    )


def _pending_triggered(
    *,
    current: Decimal,
    previous: Decimal | None,
    anchor: Decimal,
    reference: Decimal,
    thresholds: PriceDropThresholds,
) -> bool:
    if current >= anchor:
        return False
    if current >= reference:
        return False
    prior = _effective_prior(reference, previous)
    return _meets_drop_thresholds(
        prior=prior,
        current=current,
        thresholds=thresholds,
    )


def update_field_drop_state(
    state: FieldDropState,
    *,
    current: Decimal,
    previous: Decimal | None,
    reference: Decimal,
    thresholds: PriceDropThresholds,
    now: datetime,
) -> tuple[FieldDropState, PriceDropRecord | None, PriceDropRecord | None]:
    result = _update_field_drop_state(
        state,
        current=current,
        previous=previous,
        reference=reference,
        thresholds=thresholds,
        now=now,
    )
    return result.state, result.confirmed, result.recovered


def _update_field_drop_state(
    state: FieldDropState,
    *,
    current: Decimal,
    previous: Decimal | None,
    reference: Decimal,
    thresholds: PriceDropThresholds,
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
    state: FieldDropState,
    *,
    current: Decimal,
    previous: Decimal | None,
    reference: Decimal,
    thresholds: PriceDropThresholds,
    now: datetime,
) -> FieldUpdateResult:
    if not _pending_triggered(
        current=current,
        previous=previous,
        anchor=state.anchor,
        reference=reference,
        thresholds=thresholds,
    ):
        if current > state.anchor:
            return FieldUpdateResult(
                state=state.model_copy(update={"anchor": current}),
                confirmed=None,
                recovered=None,
            )
        return FieldUpdateResult(state=state, confirmed=None, recovered=None)

    return FieldUpdateResult(
        state=state.model_copy(
            update={
                "status": "pending",
                "pending_price": current,
                "pending_builds": 1,
                "episode_start_price": state.anchor,
            },
        ),
        confirmed=None,
        recovered=None,
    )


def _update_pending_state(
    state: FieldDropState,
    *,
    current: Decimal,
    previous: Decimal | None,
    reference: Decimal,
    thresholds: PriceDropThresholds,
    now: datetime,
) -> FieldUpdateResult:
    assert state.pending_price is not None
    assert state.episode_start_price is not None

    if current > state.pending_price and not _prices_match(
        current, state.pending_price
    ):
        return FieldUpdateResult(
            state=FieldDropState.idle(state.anchor),
            confirmed=None,
            recovered=None,
        )

    if current < state.pending_price and not _prices_match(
        current, state.pending_price
    ):
        if _pending_triggered(
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
            state=FieldDropState.idle(state.anchor),
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
    state: FieldDropState,
    *,
    current: Decimal,
    previous: Decimal | None,
    reference: Decimal,
    thresholds: PriceDropThresholds,
    now: datetime,
) -> FieldUpdateResult:
    assert state.episode_start_price is not None
    assert state.confirmed_price is not None

    recovery_threshold = state.episode_start_price * RECOVERY_FACTOR
    if current > recovery_threshold:
        recovery_builds = state.recovery_builds + 1
        if recovery_builds >= RECOVERY_BUILDS:
            recovered = _episode_from_confirmation(
                model_id="",
                field="",
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
                state=FieldDropState.idle(current),
                confirmed=None,
                recovered=recovered,
            )
        return FieldUpdateResult(
            state=state.model_copy(update={"recovery_builds": recovery_builds}),
            confirmed=None,
            recovered=None,
        )

    if (
        current < state.confirmed_price
        and not _prices_match(current, state.confirmed_price)
        and _pending_triggered(
            current=current,
            previous=previous,
            anchor=state.anchor,
            reference=reference,
            thresholds=thresholds,
        )
    ):
        return FieldUpdateResult(
            state=state.model_copy(
                update={
                    "status": "pending",
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


def update_model_field_states(
    store: PriceDropStateStore,
    *,
    model_id: str,
    current_per_million: dict[str, Decimal],
    previous_per_million: dict[str, Decimal] | None,
    reference_per_million: dict[str, Decimal],
    thresholds: PriceDropThresholds,
    now: datetime,
) -> tuple[PriceDropStateStore, list[PriceDropRecord], list[PriceDropRecord]]:
    model_states = dict(store.models.get(model_id, {}))
    episodes = list(store.episodes)
    confirmed_episodes: list[PriceDropRecord] = []
    recovered_episodes: list[PriceDropRecord] = []

    for field, reference in reference_per_million.items():
        current = current_per_million.get(field)
        if current is None or current <= 0:
            continue

        previous = previous_per_million.get(field) if previous_per_million else None
        field_state = model_states.get(field)
        if field_state is None:
            field_state = FieldDropState.idle(current)

        new_state, confirmed, recovered = update_field_drop_state(
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
    )


def _mark_latest_episode_recovered(
    episodes: list[PriceDropRecord],
    *,
    model_id: str,
    field: str,
    recovered_price: Decimal,
    recovered_at: datetime,
) -> PriceDropRecord | None:
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


def active_drops_from_state(store: PriceDropStateStore) -> list[PriceDropRecord]:
    active: list[PriceDropRecord] = []
    for model_id, fields in store.models.items():
        for field, field_state in fields.items():
            if field_state.status != "confirmed":
                continue
            if (
                field_state.episode_start_price is None
                or field_state.confirmed_price is None
            ):
                continue
            active.append(
                _episode_from_confirmation(
                    model_id=model_id,
                    field=field,
                    episode_start=field_state.episode_start_price,
                    confirmed_price=field_state.confirmed_price,
                    detected_at=field_state.confirmed_at or store.generated_at,
                ),
            )
    return active


def close_orphaned_active_episodes(
    episodes: list[PriceDropRecord],
    models: dict[str, dict[str, FieldDropState]],
    *,
    now: datetime,
    current_per_million_by_model: dict[str, dict[str, Decimal]] | None = None,
) -> list[PriceDropRecord]:
    healed: list[PriceDropRecord] = []
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
