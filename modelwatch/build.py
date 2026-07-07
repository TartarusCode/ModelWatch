import asyncio
import json
import logging
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from modelwatch.aa_scores import summarize_artificial_analysis
from modelwatch.fetch import (
    fetch_all_benchmarks,
    fetch_all_provider_endpoints,
    fetch_models_async,
)
from modelwatch.history import load_history, merge_build_into_history, save_history
from modelwatch.json_output import dump_model_line, write_model_json
from modelwatch.model_filters import is_latest_alias_model_id
from modelwatch.new_models import (
    NEW_MODEL_LOOKBACK_HOURS,
    NewModelAddition,
    detect_new_models,
    load_new_model_events,
    models_in_last_hours,
)
from modelwatch.price_baselines import compute_moving_average_per_field
from modelwatch.price_drop_state import (
    load_price_drop_state,
    save_price_drop_state,
    update_model_field_states,
)
from modelwatch.price_events import (
    DROP_LOOKBACK_HOURS,
    build_price_drops_output,
    episodes_to_event_records,
)
from modelwatch.pricing import DEFAULT_THRESHOLDS, per_million_usd
from modelwatch.provider_stats import build_benchmark_scores, build_provider_stats
from modelwatch.schemas import (
    BenchmarkFetchStatus,
    BuildMeta,
    DesignArenaBenchmarks,
    EnrichedModel,
    ModelBenchmarks,
    ModelSnapshot,
    ModelsOutput,
    NewModelEventRecord,
    NewModelsOutput,
    PreviousSnapshot,
    PriceDropRecord,
    PriceDropsOutput,
    PriceDropThresholdsOutput,
    PriceEventRecord,
)
from modelwatch.stable_output import stabilize_enriched_models

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "web" / "public" / "data"
SNAPSHOT_PATH = ROOT / "data" / "snapshots" / "previous.json"
EVENTS_PATH = DATA_DIR / "price-events.jsonl"
NEW_MODEL_EVENTS_PATH = DATA_DIR / "new-model-events.jsonl"
MAX_EVENTS = 500
DESCRIPTION_MAX_LEN = 500
logger = logging.getLogger(__name__)


def _trim_description(description: str | None) -> str | None:
    if description is None:
        return None
    if len(description) <= DESCRIPTION_MAX_LEN:
        return description
    return description[: DESCRIPTION_MAX_LEN - 3] + "..."


def _parse_model(raw: dict[str, object]) -> ModelSnapshot | None:
    trimmed = {**raw}
    description = trimmed.get("description")
    if isinstance(description, str):
        trimmed["description"] = _trim_description(description)
    try:
        return ModelSnapshot.model_validate(trimmed)
    except ValidationError as exc:
        model_id = trimmed.get("id", "<unknown>")
        logger.warning("Skipping invalid model %s: %s", model_id, exc)
        return None


def _pricing_dict(pricing: ModelSnapshot) -> dict[str, str]:
    raw = pricing.pricing.model_dump(exclude_none=True)
    return {key: str(value) for key, value in raw.items()}


def _previous_per_million(
    previous: PreviousSnapshot | None,
    model_id: str,
) -> dict[str, Decimal] | None:
    if previous is None:
        return None
    snapshot = previous.models.get(model_id)
    if snapshot is None:
        return None
    result: dict[str, Decimal] = {}
    for field, value in _pricing_dict(snapshot).items():
        try:
            result[field] = per_million_usd(value)
        except ValueError:
            continue
    return result or None


def _current_per_million(model: ModelSnapshot) -> dict[str, Decimal]:
    result: dict[str, Decimal] = {}
    for field, value in _pricing_dict(model).items():
        try:
            result[field] = per_million_usd(value)
        except ValueError:
            continue
    return result


def _load_previous() -> PreviousSnapshot | None:
    if not SNAPSHOT_PATH.exists():
        return None
    payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    return PreviousSnapshot.model_validate(payload)


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


def _sync_price_events_jsonl(episodes: list[PriceDropRecord]) -> None:
    lines = [dump_model_line(event) for event in episodes_to_event_records(episodes)]
    trimmed = lines[-MAX_EVENTS:]
    EVENTS_PATH.write_text(
        "\n".join(trimmed) + ("\n" if trimmed else ""),
        encoding="utf-8",
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
        design_status = BenchmarkFetchStatus(status="error", error=str(design_error))
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

    benchmark_scores_raw = raw.get("benchmark_scores")
    benchmark_scores_error = raw.get("benchmark_scores_error")
    benchmark_scores, benchmark_scores_status = build_benchmark_scores(
        benchmark_scores_raw if isinstance(benchmark_scores_raw, dict) else None,
        error=str(benchmark_scores_error)
        if benchmark_scores_error is not None
        else None,
    )

    return ModelBenchmarks(
        design_arena=design_parsed,
        design_arena_status=design_status,
        artificial_analysis=aa_records,
        artificial_analysis_status=aa_status,
        artificial_analysis_summary=None,
        benchmark_scores=benchmark_scores,
        benchmark_scores_status=benchmark_scores_status,
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
    model_ids = [model.id for model in snapshots]
    benchmark_raw, endpoints_raw = await asyncio.gather(
        fetch_all_benchmarks(canonical_slugs),
        fetch_all_provider_endpoints(model_ids),
    )
    benchmark_by_canonical = {
        str(item["canonical_slug"]): item
        for item in benchmark_raw
        if isinstance(item.get("canonical_slug"), str)
    }
    endpoints_by_model = {
        str(item["model_id"]): item
        for item in endpoints_raw
        if isinstance(item.get("model_id"), str)
    }

    enriched: list[EnrichedModel] = []
    benchmark_errors = 0
    benchmark_empty = 0
    for model in snapshots:
        raw_bench = benchmark_by_canonical.get(model.canonical_slug, {})
        effective_pricing_raw = raw_bench.get("effective_pricing")
        endpoints_payload = endpoints_by_model.get(model.id, {})
        provider_endpoints_raw = endpoints_payload.get("endpoints")
        benchmarks = _attach_aa_summary(
            _build_benchmarks(raw_bench),
            model_id=model.id,
        )
        provider_stats = build_provider_stats(
            effective_pricing_raw=effective_pricing_raw
            if isinstance(effective_pricing_raw, dict)
            else None,
            effective_pricing_error=str(raw_bench["effective_pricing_error"])
            if raw_bench.get("effective_pricing_error") is not None
            else None,
            endpoints_raw=provider_endpoints_raw
            if isinstance(provider_endpoints_raw, dict)
            else None,
            endpoints_error=str(endpoints_payload["endpoints_error"])
            if endpoints_payload.get("endpoints_error") is not None
            else None,
        )
        for status in (
            benchmarks.design_arena_status,
            benchmarks.artificial_analysis_status,
            benchmarks.benchmark_scores_status,
            provider_stats.effective_pricing_status,
        ):
            if status.status == "error":
                benchmark_errors += 1
            elif status.status == "empty":
                benchmark_empty += 1
        enriched.append(
            EnrichedModel(
                model=model,
                benchmarks=benchmarks,
                provider_stats=provider_stats,
            )
        )

    enriched = stabilize_enriched_models(enriched)

    previous = _load_previous()
    new_additions = detect_new_models(snapshots, previous=previous)
    history = load_history()
    drop_state = load_price_drop_state()
    current_per_million_by_model: dict[str, dict[str, Decimal]] = {}
    for model in snapshots:
        if is_latest_alias_model_id(model.id):
            continue
        history_points = history.models.get(model.id, [])
        moving_average = compute_moving_average_per_field(
            history_points,
            now=started,
        )
        if not moving_average:
            continue
        current_per_million = _current_per_million(model)
        current_per_million_by_model[model.id] = current_per_million
        drop_state, _, _ = update_model_field_states(
            drop_state,
            model_id=model.id,
            current_per_million=current_per_million,
            previous_per_million=_previous_per_million(previous, model.id),
            reference_per_million=moving_average,
            thresholds=DEFAULT_THRESHOLDS,
            now=started,
        )

    save_price_drop_state(drop_state)
    _sync_price_events_jsonl(drop_state.episodes)

    new_model_event_records = [
        _addition_to_event(addition, started) for addition in new_additions
    ]
    _append_new_model_events(new_model_event_records)

    finished = datetime.now(UTC)
    active_drops, recovered_drops, episodes = build_price_drops_output(
        drop_state.episodes,
        current_per_million_by_model=current_per_million_by_model,
        now=finished,
        window_hours=DROP_LOOKBACK_HOURS,
        thresholds=DEFAULT_THRESHOLDS,
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
        active_drops=active_drops,
        recovered_drops=recovered_drops,
        episodes=episodes,
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
