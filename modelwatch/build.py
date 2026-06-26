import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from modelwatch.aa_scores import summarize_artificial_analysis
from modelwatch.fetch import fetch_all_benchmarks, fetch_models_async
from modelwatch.model_filters import is_latest_alias_model_id
from modelwatch.json_output import dump_model_line, write_model_json
from modelwatch.history import merge_build_into_history, save_history, load_history
from modelwatch.new_models import (
    NEW_MODEL_LOOKBACK_HOURS,
    NewModelAddition,
    detect_new_models,
    load_new_model_events,
    models_in_last_hours,
)
from modelwatch.price_baselines import (
    apply_drop_ratchet,
    build_reference_per_million,
    compute_moving_average_per_field,
    load_baselines,
    save_baselines,
)
from modelwatch.price_events import (
    DROP_LOOKBACK_HOURS,
    drops_in_last_hours,
    filter_redundant_drop_events,
    load_price_events,
)
from modelwatch.pricing import (
    DEFAULT_THRESHOLDS,
    PriceDrop,
    detect_price_drops_from_reference,
)
from modelwatch.stable_output import stabilize_enriched_models
from modelwatch.schemas import (
    BenchmarkFetchStatus,
    BuildMeta,
    DesignArenaBenchmarks,
    EnrichedModel,
    ModelBenchmarks,
    ModelSnapshot,
    ModelsOutput,
    PreviousSnapshot,
    NewModelEventRecord,
    NewModelsOutput,
    PriceDropRecord,
    PriceDropsOutput,
    PriceDropThresholdsOutput,
    PriceEventRecord,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "web" / "public" / "data"
SNAPSHOT_PATH = ROOT / "data" / "snapshots" / "previous.json"
EVENTS_PATH = DATA_DIR / "price-events.jsonl"
NEW_MODEL_EVENTS_PATH = DATA_DIR / "new-model-events.jsonl"
MAX_EVENTS = 500
DESCRIPTION_MAX_LEN = 500


def _trim_description(description: str | None) -> str | None:
    if description is None:
        return None
    if len(description) <= DESCRIPTION_MAX_LEN:
        return description
    return description[: DESCRIPTION_MAX_LEN - 3] + "..."


def _parse_model(raw: dict[str, object]) -> ModelSnapshot | None:
    trimmed = {**raw}
    if isinstance(trimmed.get("description"), str):
        trimmed["description"] = _trim_description(trimmed["description"])
    try:
        return ModelSnapshot.model_validate(trimmed)
    except ValidationError:
        return None


def _pricing_dict(pricing: ModelSnapshot) -> dict[str, str]:
    raw = pricing.pricing.model_dump(exclude_none=True)
    return {key: str(value) for key, value in raw.items()}


def _load_previous() -> PreviousSnapshot | None:
    if not SNAPSHOT_PATH.exists():
        return None
    payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    return PreviousSnapshot.model_validate(payload)


def _drop_to_record(drop: PriceDrop, detected_at: datetime) -> PriceDropRecord:
    return PriceDropRecord(
        detected_at=detected_at,
        model_id=drop.model_id,
        field=drop.field,
        old_per_million_usd=f"{drop.old_per_million_usd:.6f}",
        new_per_million_usd=f"{drop.new_per_million_usd:.6f}",
        pct_drop=float(drop.pct_drop),
        saved_per_million_usd=f"{drop.saved_per_million_usd:.6f}",
    )


def _addition_to_event(
    addition: NewModelAddition,
    detected_at: datetime,
) -> NewModelEventRecord:
    return NewModelEventRecord(
        detected_at=detected_at,
        model_id=addition.model_id,
        name=addition.name,
        canonical_slug=addition.canonical_slug,
        created=addition.created,
    )


def _drop_to_event(drop: PriceDrop, detected_at: datetime) -> PriceEventRecord:
    return PriceEventRecord(
        detected_at=detected_at,
        model_id=drop.model_id,
        field=drop.field,
        old_per_million_usd=f"{drop.old_per_million_usd:.6f}",
        new_per_million_usd=f"{drop.new_per_million_usd:.6f}",
        pct_drop=float(drop.pct_drop),
        saved_per_million_usd=f"{drop.saved_per_million_usd:.6f}",
    )


def _append_jsonl_events(
    path: Path,
    events: list[PriceEventRecord] | list[NewModelEventRecord],
) -> None:
    if not events:
        return
    existing: list[str] = []
    if path.exists():
        existing = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    new_lines = [dump_model_line(event) for event in events]
    combined = existing + new_lines
    trimmed = combined[-MAX_EVENTS:]
    path.write_text("\n".join(trimmed) + "\n", encoding="utf-8")


def _append_price_events(events: list[PriceEventRecord]) -> None:
    _append_jsonl_events(EVENTS_PATH, events)


def _append_new_model_events(events: list[NewModelEventRecord]) -> None:
    _append_jsonl_events(NEW_MODEL_EVENTS_PATH, events)


def _build_benchmarks(raw: dict[str, object]) -> ModelBenchmarks:
    design_raw = raw.get("design_arena")
    design_error = raw.get("design_arena_error")
    aa_raw = raw.get("artificial_analysis")
    aa_error = raw.get("artificial_analysis_error")

    design_status: BenchmarkFetchStatus
    design_parsed: DesignArenaBenchmarks | None = None
    if design_error is not None:
        design_status = BenchmarkFetchStatus(
            status="error", error=str(design_error)
        )
    elif isinstance(design_raw, dict):
        records = design_raw.get("records")
        if isinstance(records, list) and len(records) > 0:
            elo_bounds = design_raw.get("eloBounds")
            bounds = elo_bounds if isinstance(elo_bounds, dict) else None
            design_parsed = DesignArenaBenchmarks(
                records=[r for r in records if isinstance(r, dict)],
                elo_bounds={
                    str(k): int(v)
                    for k, v in bounds.items()
                    if isinstance(v, (int, float))
                }
                if bounds
                else None,
            )
            design_status = BenchmarkFetchStatus(status="ok")
        else:
            design_status = BenchmarkFetchStatus(status="empty")
    else:
        design_status = BenchmarkFetchStatus(status="error", error="missing data")

    aa_status: BenchmarkFetchStatus
    aa_records: list[dict[str, object]] = []
    if aa_error is not None:
        aa_status = BenchmarkFetchStatus(status="error", error=str(aa_error))
    elif isinstance(aa_raw, list):
        aa_records = [item for item in aa_raw if isinstance(item, dict)]
        aa_status = (
            BenchmarkFetchStatus(status="ok")
            if aa_records
            else BenchmarkFetchStatus(status="empty")
        )
    else:
        aa_status = BenchmarkFetchStatus(status="error", error="missing data")

    return ModelBenchmarks(
        design_arena=design_parsed,
        design_arena_status=design_status,
        artificial_analysis=aa_records,
        artificial_analysis_status=aa_status,
        artificial_analysis_summary=None,
    )


def _attach_aa_summary(
    benchmarks: ModelBenchmarks,
    *,
    model_id: str,
) -> ModelBenchmarks:
    if benchmarks.artificial_analysis_status.status != "ok":
        return benchmarks
    summary = summarize_artificial_analysis(
        benchmarks.artificial_analysis,
        model_id=model_id,
    )
    if summary is None:
        return benchmarks
    return benchmarks.model_copy(
        update={"artificial_analysis_summary": summary},
    )


async def run_build() -> None:
    started = datetime.now(UTC)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)

    raw_models = await fetch_models_async()
    snapshots: list[ModelSnapshot] = []
    for raw in raw_models:
        parsed = _parse_model(raw)
        if parsed is not None and not is_latest_alias_model_id(parsed.id):
            snapshots.append(parsed)

    canonical_slugs = sorted({model.canonical_slug for model in snapshots})
    benchmark_raw = await fetch_all_benchmarks(canonical_slugs)
    benchmark_by_canonical = {
        str(item["canonical_slug"]): item
        for item in benchmark_raw
        if isinstance(item.get("canonical_slug"), str)
    }

    enriched: list[EnrichedModel] = []
    benchmark_errors = 0
    benchmark_empty = 0
    for model in snapshots:
        raw_bench = benchmark_by_canonical.get(model.canonical_slug, {})
        benchmarks = _attach_aa_summary(
            _build_benchmarks(raw_bench),
            model_id=model.id,
        )
        if benchmarks.design_arena_status.status == "error":
            benchmark_errors += 1
        elif benchmarks.design_arena_status.status == "empty":
            benchmark_empty += 1
        if benchmarks.artificial_analysis_status.status == "error":
            benchmark_errors += 1
        elif benchmarks.artificial_analysis_status.status == "empty":
            benchmark_empty += 1
        enriched.append(EnrichedModel(model=model, benchmarks=benchmarks))

    enriched = stabilize_enriched_models(enriched)

    previous = _load_previous()
    new_additions = detect_new_models(snapshots, previous=previous)
    history = load_history()
    baselines = load_baselines()
    all_drops: list[PriceDrop] = []
    for model in snapshots:
        history_points = history.models.get(model.id, [])
        moving_average = compute_moving_average_per_field(
            history_points,
            now=started,
        )
        if not moving_average:
            continue
        reference_per_million, baseline_per_million = build_reference_per_million(
            moving_average=moving_average,
            baselines=baselines,
            model_id=model.id,
        )
        drops = detect_price_drops_from_reference(
            model_id=model.id,
            current_pricing=_pricing_dict(model),
            reference_per_million=reference_per_million,
            baseline_per_million=baseline_per_million or None,
            thresholds=DEFAULT_THRESHOLDS,
        )
        all_drops.extend(drops)

    new_model_event_records = [
        _addition_to_event(addition, started) for addition in new_additions
    ]
    _append_new_model_events(new_model_event_records)

    event_records = [_drop_to_event(drop, started) for drop in all_drops]
    existing_events = load_price_events(EVENTS_PATH)
    event_records = filter_redundant_drop_events(
        event_records,
        existing=existing_events,
    )
    _append_price_events(event_records)
    baselines = apply_drop_ratchet(baselines, all_drops, updated_at=started)
    save_baselines(baselines)

    finished = datetime.now(UTC)
    all_events = load_price_events(EVENTS_PATH)
    drop_records = drops_in_last_hours(
        all_events,
        DROP_LOOKBACK_HOURS,
        now=finished,
    )

    all_new_model_events = load_new_model_events(NEW_MODEL_EVENTS_PATH)
    new_model_records = models_in_last_hours(
        all_new_model_events,
        NEW_MODEL_LOOKBACK_HOURS,
        now=finished,
    )

    models_output = ModelsOutput(generated_at=started, models=enriched)
    new_models_output = NewModelsOutput(
        generated_at=finished,
        window_hours=NEW_MODEL_LOOKBACK_HOURS,
        models=new_model_records,
    )
    drops_output = PriceDropsOutput(
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
    meta = BuildMeta(
        generated_at=finished,
        model_count=len(enriched),
        build_duration_seconds=(finished - started).total_seconds(),
        benchmark_errors=benchmark_errors,
        benchmark_empty=benchmark_empty,
    )

    write_model_json(DATA_DIR / "models.json", models_output)
    write_model_json(DATA_DIR / "price-drops.json", drops_output)
    write_model_json(DATA_DIR / "new-models.json", new_models_output)
    write_model_json(DATA_DIR / "meta.json", meta)

    previous_output = PreviousSnapshot(
        generated_at=finished,
        models={model.id: model for model in snapshots},
    )
    write_model_json(SNAPSHOT_PATH, previous_output)

    history = merge_build_into_history(
        [(model.id, model.pricing) for model in snapshots],
        recorded_at=finished,
    )
    save_history(history)


def main() -> None:
    asyncio.run(run_build())


if __name__ == "__main__":
    main()
