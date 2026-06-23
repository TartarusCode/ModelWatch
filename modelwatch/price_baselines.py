from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from modelwatch.history import PriceHistoryPoint, _per_million_field_name
from modelwatch.json_output import write_model_json
from modelwatch.pricing import PRICING_FIELDS, PriceDrop
from modelwatch.schemas import PriceDropBaselinesStore

MA_WINDOW_DAYS = 7
MIN_MA_POINTS = 3

BASELINES_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "snapshots" / "price-drop-baselines.json"
)


def reference_price(moving_avg: Decimal, baseline: Decimal | None) -> Decimal:
    if baseline is None:
        return moving_avg
    return max(moving_avg, baseline)


def compute_moving_average_per_field(
    history_points: list[PriceHistoryPoint],
    *,
    now: datetime,
    window_days: int = MA_WINDOW_DAYS,
    min_points: int = MIN_MA_POINTS,
) -> dict[str, Decimal]:
    cutoff = now - timedelta(days=window_days)
    in_window = [point for point in history_points if point.recorded_at >= cutoff]
    if len(in_window) < min_points:
        return {}

    averages: dict[str, Decimal] = {}
    for field in PRICING_FIELDS:
        attr = _per_million_field_name(field)
        values = [
            value
            for point in in_window
            if (value := getattr(point, attr)) is not None and value > 0
        ]
        if len(values) < min_points:
            continue
        averages[field] = sum(values, start=Decimal(0)) / Decimal(len(values))
    return averages


def load_baselines() -> PriceDropBaselinesStore:
    if not BASELINES_PATH.exists():
        now = datetime.now(UTC)
        return PriceDropBaselinesStore(generated_at=now, models={})
    import json

    payload = json.loads(BASELINES_PATH.read_text(encoding="utf-8"))
    return PriceDropBaselinesStore.model_validate(payload)


def save_baselines(store: PriceDropBaselinesStore) -> None:
    BASELINES_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_model_json(BASELINES_PATH, store)


def apply_drop_ratchet(
    store: PriceDropBaselinesStore,
    drops: list[PriceDrop],
    *,
    updated_at: datetime,
) -> PriceDropBaselinesStore:
    if not drops:
        return store

    updated_models = {model_id: dict(fields) for model_id, fields in store.models.items()}
    for drop in drops:
        model_fields = dict(updated_models.get(drop.model_id, {}))
        new_value = f"{drop.new_per_million_usd:.6f}"
        existing = model_fields.get(drop.field)
        if existing is None or Decimal(existing) > drop.new_per_million_usd:
            model_fields[drop.field] = new_value
        updated_models[drop.model_id] = model_fields

    return PriceDropBaselinesStore(
        generated_at=updated_at,
        models=updated_models,
    )


def build_reference_per_million(
    *,
    moving_average: dict[str, Decimal],
    baselines: PriceDropBaselinesStore,
    model_id: str,
) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    model_baselines = baselines.models.get(model_id, {})
    references: dict[str, Decimal] = {}
    baseline_per_million: dict[str, Decimal] = {}
    for field, moving_avg in moving_average.items():
        baseline_raw = model_baselines.get(field)
        baseline = Decimal(baseline_raw) if baseline_raw is not None else None
        references[field] = reference_price(moving_avg, baseline)
        if baseline is not None:
            baseline_per_million[field] = baseline
    return references, baseline_per_million
