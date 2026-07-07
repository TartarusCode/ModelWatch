from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from modelwatch.history import (
    PriceHistoryPoint,
    load_history,
    migrate_monolith_history_to_split,
    repair_model_history_filenames,
    save_history,
)
from modelwatch.json_output import dump_model_line, write_model_json
from modelwatch.model_filters import is_latest_alias_model_id
from modelwatch.new_models import load_new_model_events
from modelwatch.price_drop_state import (
    STATE_PATH,
    PriceDropStateStore,
    is_episode_active,
    load_price_drop_state,
    save_price_drop_state,
)
from modelwatch.price_events import (
    DROP_LOOKBACK_HOURS,
    build_price_drops_output,
    episodes_to_event_records,
    filter_spurious_zero_drop_events,
    load_price_events,
)
from modelwatch.pricing import DEFAULT_THRESHOLDS, per_million_usd
from modelwatch.pricing_glitch import is_paid_zero_glitch_point
from modelwatch.schemas import (
    ModelsOutput,
    NewModelEventRecord,
    PriceDropRecord,
    PriceDropsOutput,
    PriceDropThresholdsOutput,
    PriceEventRecord,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "web" / "public" / "data"
EVENTS_PATH = DATA_DIR / "price-events.jsonl"
NEW_MODEL_EVENTS_PATH = DATA_DIR / "new-model-events.jsonl"
PRICE_DROPS_PATH = DATA_DIR / "price-drops.json"
MODELS_PATH = DATA_DIR / "models.json"
BASELINES_PATH = (
    ROOT / "data" / "snapshots" / "price-drop-baselines.json"
)


def filter_price_events(events: list[PriceEventRecord]) -> list[PriceEventRecord]:
    filtered = [
        event for event in events if not is_latest_alias_model_id(event.model_id)
    ]
    return filter_spurious_zero_drop_events(filtered)


def filter_new_model_events(
    events: list[NewModelEventRecord],
) -> list[NewModelEventRecord]:
    return [event for event in events if not is_latest_alias_model_id(event.model_id)]


def write_jsonl_events(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _upgrade_legacy_event(raw: dict[str, object]) -> PriceEventRecord:
    episode_start = raw.get("episode_start_per_million_usd")
    if episode_start is None:
        raw = {
            **raw,
            "episode_start_per_million_usd": raw.get("old_per_million_usd"),
            "status": raw.get("status", "active"),
        }
    return PriceEventRecord.model_validate(raw)


def migrate_legacy_price_events(
    events: list[PriceEventRecord],
) -> list[PriceDropRecord]:
    migrated: list[PriceDropRecord] = []
    for event in events:
        payload = event.model_dump()
        if payload.get("episode_start_per_million_usd") is None:
            payload["episode_start_per_million_usd"] = event.old_per_million_usd
        if payload.get("status") is None:
            payload["status"] = "active"
        migrated.append(PriceDropRecord.model_validate(payload))
    return migrated


def _current_per_million_by_model() -> dict[str, dict[str, Decimal]]:
    if not MODELS_PATH.exists():
        return {}
    models_output = ModelsOutput.model_validate_json(
        MODELS_PATH.read_text(encoding="utf-8"),
    )
    result: dict[str, dict[str, Decimal]] = {}
    for enriched in models_output.models:
        model_id = enriched.model.id
        fields: dict[str, Decimal] = {}
        pricing = enriched.model.pricing.model_dump(exclude_none=True)
        for field, value in pricing.items():
            try:
                fields[field] = per_million_usd(str(value))
            except ValueError:
                continue
        if fields:
            result[model_id] = fields
    return result


def reconcile_episode_statuses(
    episodes: list[PriceDropRecord],
    *,
    current_per_million_by_model: dict[str, dict[str, Decimal]],
    now: datetime,
) -> list[PriceDropRecord]:
    reconciled: list[PriceDropRecord] = []
    for episode in episodes:
        if episode.status == "recovered":
            reconciled.append(episode)
            continue
        current = current_per_million_by_model.get(episode.model_id, {}).get(
            episode.field,
        )
        if current is None:
            reconciled.append(episode)
            continue
        if is_episode_active(episode, current):
            reconciled.append(episode)
            continue
        reconciled.append(
            episode.model_copy(
                update={
                    "status": "recovered",
                    "recovered_at": episode.recovered_at or now,
                    "recovered_per_million_usd": f"{current:.6f}",
                },
            ),
        )
    return reconciled


def clean_price_events_file(path: Path | None = None) -> int:
    target = path or EVENTS_PATH
    events = load_price_events(target)
    migrated = migrate_legacy_price_events(filter_price_events(events))
    current = _current_per_million_by_model()
    reconciled = reconcile_episode_statuses(
        migrated,
        current_per_million_by_model=current,
        now=datetime.now(UTC),
    )
    removed = len(events) - len(reconciled)
    write_jsonl_events(
        target,
        [dump_model_line(event) for event in episodes_to_event_records(reconciled)],
    )
    return max(removed, 0)


def clean_new_model_events_file(path: Path | None = None) -> int:
    target = path or NEW_MODEL_EVENTS_PATH
    events = load_new_model_events(target)
    kept = filter_new_model_events(events)
    removed = len(events) - len(kept)
    if removed:
        write_jsonl_events(target, [dump_model_line(event) for event in kept])
    return removed


def clean_price_history() -> int:
    store = load_history()
    removed = 0
    kept_models: dict[str, list[PriceHistoryPoint]] = {}
    for model_id, points in store.models.items():
        if is_latest_alias_model_id(model_id):
            removed += 1
            continue
        kept_points = [
            point
            for index, point in enumerate(points)
            if not is_paid_zero_glitch_point(model_id, points, index)
        ]
        removed += len(points) - len(kept_points)
        if kept_points:
            kept_models[model_id] = kept_points
    if removed:
        save_history(
            store.model_copy(
                update={
                    "generated_at": datetime.now(UTC),
                    "models": kept_models,
                },
            ),
        )
    return removed


def remove_legacy_baseline_file() -> bool:
    if not BASELINES_PATH.exists():
        return False
    BASELINES_PATH.unlink()
    return True


def rebuild_price_drop_state_from_events(
    *,
    now: datetime | None = None,
) -> PriceDropStateStore:
    finished = now or datetime.now(UTC)
    events = load_price_events(EVENTS_PATH)
    episodes = reconcile_episode_statuses(
        migrate_legacy_price_events(filter_price_events(events)),
        current_per_million_by_model=_current_per_million_by_model(),
        now=finished,
    )
    store = PriceDropStateStore(
        generated_at=finished,
        models={},
        episodes=episodes,
    )
    save_price_drop_state(store)
    write_jsonl_events(
        EVENTS_PATH,
        [dump_model_line(event) for event in episodes_to_event_records(episodes)],
    )
    return store


def rebuild_price_drops_output(
    *,
    now: datetime | None = None,
    path: Path = PRICE_DROPS_PATH,
) -> PriceDropsOutput:
    finished = now or datetime.now(UTC)
    store = load_price_drop_state() if STATE_PATH.exists() else None
    episodes = store.episodes if store is not None else []
    current = _current_per_million_by_model()
    active, recovered, display_episodes = build_price_drops_output(
        episodes,
        current_per_million_by_model=current,
        now=finished,
        window_hours=DROP_LOOKBACK_HOURS,
        thresholds=DEFAULT_THRESHOLDS,
    )
    output = PriceDropsOutput(
        generated_at=finished,
        window_hours=DROP_LOOKBACK_HOURS,
        thresholds=PriceDropThresholdsOutput(
            min_pct=float(DEFAULT_THRESHOLDS.min_pct),
            min_saved_per_million_usd=float(
                DEFAULT_THRESHOLDS.min_saved_per_million_usd
            ),
        ),
        active_drops=active,
        recovered_drops=recovered,
        episodes=display_episodes,
    )
    write_model_json(path, output)
    return output


def clean_alias_artifacts() -> dict[str, int | bool]:
    migrated = migrate_monolith_history_to_split()
    return {
        "price_history_migrated": migrated,
        "price_history_filenames_repaired": repair_model_history_filenames(),
        "price_events_removed": clean_price_events_file(),
        "new_model_events_removed": clean_new_model_events_file(),
        "price_history_models_removed": clean_price_history(),
        "legacy_baselines_removed": remove_legacy_baseline_file(),
    }


def main() -> None:
    counts = clean_alias_artifacts()
    rebuild_price_drop_state_from_events()
    output = rebuild_price_drops_output()
    print(counts)
    print(f"active_drops={len(output.active_drops)}")
    print(f"recovered_drops={len(output.recovered_drops)}")
    print(f"episodes={len(output.episodes)}")


if __name__ == "__main__":
    main()
