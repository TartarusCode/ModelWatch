from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from modelwatch.history import PriceHistoryPoint, load_history, save_history
from modelwatch.json_output import dump_model_line, write_model_json
from modelwatch.model_filters import is_latest_alias_model_id
from modelwatch.new_models import (
    load_new_model_events,
)
from modelwatch.price_baselines import load_baselines, save_baselines
from modelwatch.price_events import (
    DROP_LOOKBACK_HOURS,
    dedupe_settled_price_re_alerts,
    drops_in_last_hours,
    filter_spurious_zero_drop_events,
    load_price_events,
)
from modelwatch.pricing import DEFAULT_THRESHOLDS
from modelwatch.pricing_glitch import (
    is_free_model_id,
    is_paid_zero_glitch_point,
)
from modelwatch.schemas import (
    NewModelEventRecord,
    PriceDropsOutput,
    PriceDropThresholdsOutput,
    PriceEventRecord,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "web" / "public" / "data"
EVENTS_PATH = DATA_DIR / "price-events.jsonl"
NEW_MODEL_EVENTS_PATH = DATA_DIR / "new-model-events.jsonl"
PRICE_DROPS_PATH = DATA_DIR / "price-drops.json"


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


def clean_price_events_file(path: Path | None = None) -> int:
    target = path or EVENTS_PATH
    events = load_price_events(target)
    kept = dedupe_settled_price_re_alerts(filter_price_events(events))
    removed = len(events) - len(kept)
    if removed:
        write_jsonl_events(target, [dump_model_line(event) for event in kept])
    return removed


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


def clean_price_drop_baselines() -> int:
    store = load_baselines()
    removed = 0
    kept_models: dict[str, dict[str, str]] = {}
    for model_id, fields in store.models.items():
        if is_latest_alias_model_id(model_id):
            removed += 1
            continue
        kept_fields = {
            field: value
            for field, value in fields.items()
            if not (not is_free_model_id(model_id) and Decimal(value) <= 0)
        }
        removed += len(fields) - len(kept_fields)
        if kept_fields:
            kept_models[model_id] = kept_fields
    if removed:
        save_baselines(
            store.model_copy(
                update={
                    "generated_at": datetime.now(UTC),
                    "models": kept_models,
                },
            ),
        )
    return removed


def rebuild_price_drops_output(
    *,
    now: datetime | None = None,
    path: Path = PRICE_DROPS_PATH,
) -> PriceDropsOutput:
    finished = now or datetime.now(UTC)
    events = load_price_events(EVENTS_PATH)
    drop_records = drops_in_last_hours(
        events,
        DROP_LOOKBACK_HOURS,
        now=finished,
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
        drops=drop_records,
    )
    write_model_json(path, output)
    return output


def clean_alias_artifacts() -> dict[str, int]:
    return {
        "price_events_removed": clean_price_events_file(),
        "new_model_events_removed": clean_new_model_events_file(),
        "price_history_models_removed": clean_price_history(),
        "baseline_models_removed": clean_price_drop_baselines(),
    }


def main() -> None:
    counts = clean_alias_artifacts()
    output = rebuild_price_drops_output()
    print(counts)
    print(f"price_drops_count={len(output.drops)}")


if __name__ == "__main__":
    main()
