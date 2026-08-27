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
from modelwatch.price_change_state import (
    STATE_PATH,
    PriceChangeStateStore,
    close_orphaned_active_changes,
    load_price_change_state,
    save_price_change_state,
)
from modelwatch.price_changes import (
    CHANGE_LOOKBACK_HOURS,
    build_price_changes_output,
    episodes_to_event_records,
    filter_spurious_zero_change_events,
    load_price_change_events,
    migrate_legacy_change_event_dict,
)
from modelwatch.pricing import DEFAULT_THRESHOLDS, per_million_usd
from modelwatch.pricing_glitch import is_paid_zero_glitch_point
from modelwatch.schemas import (
    ModelsOutput,
    NewModelEventRecord,
    PriceChangeEventRecord,
    PriceChangeRecord,
    PriceChangesOutput,
    PriceChangeThresholdsOutput,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "web" / "public" / "data"
EVENTS_PATH = DATA_DIR / "price-change-events.jsonl"
LEGACY_EVENTS_PATH = DATA_DIR / "price-events.jsonl"
NEW_MODEL_EVENTS_PATH = DATA_DIR / "new-model-events.jsonl"
PRICE_CHANGES_PATH = DATA_DIR / "price-changes.json"
LEGACY_PRICE_DROPS_PATH = DATA_DIR / "price-drops.json"
MODELS_PATH = DATA_DIR / "models.json"
BASELINES_PATH = ROOT / "data" / "snapshots" / "price-drop-baselines.json"
LEGACY_STATE_PATH = ROOT / "data" / "snapshots" / "price-drop-state.json"


def filter_price_change_events(
    events: list[PriceChangeEventRecord],
) -> list[PriceChangeEventRecord]:
    filtered = [
        event for event in events if not is_latest_alias_model_id(event.model_id)
    ]
    return filter_spurious_zero_change_events(filtered)


def filter_new_model_events(
    events: list[NewModelEventRecord],
) -> list[NewModelEventRecord]:
    return [event for event in events if not is_latest_alias_model_id(event.model_id)]


def write_jsonl_events(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def migrate_legacy_price_events(
    events: list[PriceChangeEventRecord],
) -> list[PriceChangeRecord]:
    migrated: list[PriceChangeRecord] = []
    for event in events:
        payload = migrate_legacy_change_event_dict(event.model_dump())
        migrated.append(PriceChangeRecord.model_validate(payload))
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


def _resolve_events_path(path: Path | None = None) -> Path:
    if path is not None:
        return path
    if EVENTS_PATH.exists():
        return EVENTS_PATH
    if LEGACY_EVENTS_PATH.exists():
        return LEGACY_EVENTS_PATH
    return EVENTS_PATH


def clean_price_change_events_file(path: Path | None = None) -> int:
    target = _resolve_events_path(path)
    events = load_price_change_events(target)
    filtered = filter_price_change_events(events)
    migrated = migrate_legacy_price_events(filtered)
    current = _current_per_million_by_model()
    existing = load_price_change_state() if STATE_PATH.exists() else None
    models = existing.models if existing is not None else {}
    healed = close_orphaned_active_changes(
        migrated,
        models,
        now=datetime.now(UTC),
        current_per_million_by_model=current,
    )
    removed = len(events) - len(filtered)
    write_jsonl_events(
        EVENTS_PATH if path is None else target,
        [dump_model_line(event) for event in episodes_to_event_records(healed)],
    )
    if path is None and target == LEGACY_EVENTS_PATH and LEGACY_EVENTS_PATH.exists():
        LEGACY_EVENTS_PATH.unlink()
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


def migrate_legacy_state_file() -> bool:
    if STATE_PATH.exists() or not LEGACY_STATE_PATH.exists():
        return False
    import json

    payload = json.loads(LEGACY_STATE_PATH.read_text(encoding="utf-8"))
    models_raw = payload.get("models", {})
    migrated_models: dict[str, object] = {}
    if isinstance(models_raw, dict):
        for model_id, fields in models_raw.items():
            if not isinstance(fields, dict):
                continue
            migrated_fields: dict[str, object] = {}
            for field, state in fields.items():
                if not isinstance(state, dict):
                    continue
                migrated_fields[field] = {
                    **state,
                    "direction": state.get("direction")
                    or (
                        "cut"
                        if state.get("status") in ("pending", "confirmed")
                        else None
                    ),
                }
            migrated_models[str(model_id)] = migrated_fields
    episodes_raw = payload.get("episodes", [])
    migrated_episodes = []
    if isinstance(episodes_raw, list):
        for episode in episodes_raw:
            if isinstance(episode, dict):
                migrated_episodes.append(migrate_legacy_change_event_dict(episode))
    store = PriceChangeStateStore.model_validate(
        {
            "generated_at": payload.get("generated_at"),
            "models": migrated_models,
            "episodes": migrated_episodes,
        },
    )
    save_price_change_state(store)
    LEGACY_STATE_PATH.unlink()
    return True


def rebuild_price_change_state_from_events(
    *,
    now: datetime | None = None,
) -> PriceChangeStateStore:
    finished = now or datetime.now(UTC)
    migrate_legacy_state_file()
    events = load_price_change_events(_resolve_events_path())
    current = _current_per_million_by_model()
    existing = load_price_change_state() if STATE_PATH.exists() else None
    models = existing.models if existing is not None else {}
    episodes = close_orphaned_active_changes(
        migrate_legacy_price_events(filter_price_change_events(events)),
        models,
        now=finished,
        current_per_million_by_model=current,
    )
    store = PriceChangeStateStore(
        generated_at=finished,
        models=models,
        episodes=episodes,
    )
    save_price_change_state(store)
    write_jsonl_events(
        EVENTS_PATH,
        [dump_model_line(event) for event in episodes_to_event_records(episodes)],
    )
    if LEGACY_EVENTS_PATH.exists() and LEGACY_EVENTS_PATH != EVENTS_PATH:
        LEGACY_EVENTS_PATH.unlink()
    return store


def rebuild_price_changes_output(
    *,
    now: datetime | None = None,
    path: Path = PRICE_CHANGES_PATH,
) -> PriceChangesOutput:
    finished = now or datetime.now(UTC)
    store = load_price_change_state() if STATE_PATH.exists() else None
    if store is None:
        store = PriceChangeStateStore(
            generated_at=finished,
            models={},
            episodes=[],
        )
    active, recovered, settled, display_episodes = build_price_changes_output(
        store,
        now=finished,
        window_hours=CHANGE_LOOKBACK_HOURS,
    )
    output = PriceChangesOutput(
        generated_at=finished,
        window_hours=CHANGE_LOOKBACK_HOURS,
        thresholds=PriceChangeThresholdsOutput(
            min_pct=float(DEFAULT_THRESHOLDS.min_pct),
            min_delta_per_million_usd=float(
                DEFAULT_THRESHOLDS.min_delta_per_million_usd
            ),
        ),
        active_changes=active,
        recovered_changes=recovered,
        settled_changes=settled,
        episodes=display_episodes,
    )
    write_model_json(path, output)
    if LEGACY_PRICE_DROPS_PATH.exists() and path == PRICE_CHANGES_PATH:
        LEGACY_PRICE_DROPS_PATH.unlink()
    return output


def clean_alias_artifacts() -> dict[str, int | bool]:
    migrated = migrate_monolith_history_to_split()
    legacy_state_migrated = migrate_legacy_state_file()
    return {
        "price_history_migrated": migrated,
        "price_history_filenames_repaired": repair_model_history_filenames(),
        "legacy_state_migrated": legacy_state_migrated,
        "price_change_events_removed": clean_price_change_events_file(),
        "new_model_events_removed": clean_new_model_events_file(),
        "price_history_models_removed": clean_price_history(),
        "legacy_baselines_removed": remove_legacy_baseline_file(),
    }


def main() -> None:
    counts = clean_alias_artifacts()
    rebuild_price_change_state_from_events()
    output = rebuild_price_changes_output()
    print(counts)
    print(f"active_changes={len(output.active_changes)}")
    print(f"recovered_changes={len(output.recovered_changes)}")
    print(f"settled_changes={len(output.settled_changes)}")
    print(f"episodes={len(output.episodes)}")


if __name__ == "__main__":
    main()
