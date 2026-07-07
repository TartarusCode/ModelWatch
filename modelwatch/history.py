import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from modelwatch.json_output import write_model_json
from modelwatch.price_parsing import is_known_price, parse_per_token
from modelwatch.pricing import PRICING_FIELDS, per_million_field_name
from modelwatch.pricing_glitch import (
    has_recordable_history_fields,
    sanitize_history_fields,
)
from modelwatch.schemas import ModelPricing

DATA_DIR = Path(__file__).resolve().parent.parent / "web" / "public" / "data"
HISTORY_DIR = DATA_DIR / "price-history"
HISTORY_INDEX_PATH = HISTORY_DIR / "index.json"
HISTORY_MODELS_DIR = HISTORY_DIR / "models"
LEGACY_HISTORY_PATH = DATA_DIR / "price-history.json"
MAX_POINTS_PER_MODEL = 500
HEARTBEAT_HOURS = 24
_COLON_ESCAPE = "_colon_"


class PriceHistoryPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    recorded_at: datetime
    prompt_per_million: Decimal | None = None
    completion_per_million: Decimal | None = None
    image_per_million: Decimal | None = None
    request_per_million: Decimal | None = None
    internal_reasoning_per_million: Decimal | None = None
    input_cache_read_per_million: Decimal | None = None
    input_cache_write_per_million: Decimal | None = None
    web_search_per_million: Decimal | None = None


class ModelHistorySeries(BaseModel):
    model_config = ConfigDict(frozen=True)

    model_id: str
    points: list[PriceHistoryPoint]


class PriceHistoryIndex(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    model_count: int
    models: list[str]


class PriceHistoryStore(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    models: dict[str, list[PriceHistoryPoint]]


def encode_model_id(model_id: str) -> str:
    return model_id.replace("/", "__").replace(":", _COLON_ESCAPE)


def decode_model_id(encoded: str) -> str:
    return encoded.replace(_COLON_ESCAPE, ":").replace("__", "/")


def legacy_windows_broken_basename(model_id: str) -> str:
    if ":" not in model_id:
        return ""
    return model_id.replace("/", "__").split(":", maxsplit=1)[0]


def model_history_path(model_id: str) -> Path:
    return HISTORY_MODELS_DIR / f"{encode_model_id(model_id)}.json"


def _token_to_per_million(per_token: str) -> Decimal | None:
    token = parse_per_token(per_token)
    if token is None or not is_known_price(token):
        return None
    return token * Decimal(1_000_000)


def pricing_to_history_fields(pricing: ModelPricing) -> dict[str, Decimal | None]:
    raw = pricing.model_dump()
    fields: dict[str, Decimal | None] = {}
    for field in PRICING_FIELDS:
        value = raw.get(field)
        if isinstance(value, str):
            fields[field] = _token_to_per_million(value)
    return fields


def _point_pricing_values(point: PriceHistoryPoint) -> tuple[Decimal | None, ...]:
    return tuple(
        getattr(point, per_million_field_name(field)) for field in PRICING_FIELDS
    )


def _fields_match_point(
    fields: dict[str, Decimal | None],
    point: PriceHistoryPoint,
) -> bool:
    for field in PRICING_FIELDS:
        attr = per_million_field_name(field)
        if getattr(point, attr) != fields.get(field):
            return False
    return True


def _build_point(
    fields: dict[str, Decimal | None],
    recorded_at: datetime,
) -> PriceHistoryPoint:
    return PriceHistoryPoint(
        recorded_at=recorded_at,
        **{
            per_million_field_name(field): fields.get(field) for field in PRICING_FIELDS
        },
    )


def dedupe_consecutive_identical_points(
    points: list[PriceHistoryPoint],
) -> list[PriceHistoryPoint]:
    if not points:
        return []
    deduped = [points[0]]
    for point in points[1:]:
        if _point_pricing_values(point) == _point_pricing_values(deduped[-1]):
            continue
        deduped.append(point)
    return deduped


def append_build_to_history(
    store: PriceHistoryStore,
    model_id: str,
    pricing: ModelPricing,
    recorded_at: datetime,
    *,
    heartbeat_hours: int = HEARTBEAT_HOURS,
) -> tuple[PriceHistoryStore, bool]:
    existing = list(store.models.get(model_id, []))
    fields = sanitize_history_fields(
        model_id,
        pricing_to_history_fields(pricing),
        existing,
    )
    if not has_recordable_history_fields(fields):
        return store, False

    if not existing:
        point = _build_point(fields, recorded_at)
        updated_points = [point]
        dirty = True
    else:
        last_point = existing[-1]
        if not _fields_match_point(fields, last_point):
            point = _build_point(fields, recorded_at)
            updated_points = [*existing, point][-MAX_POINTS_PER_MODEL:]
            dirty = True
        else:
            age = recorded_at - last_point.recorded_at
            if age < timedelta(hours=heartbeat_hours):
                return store, False
            point = _build_point(fields, recorded_at)
            updated_points = [*existing, point][-MAX_POINTS_PER_MODEL:]
            dirty = True

    updated_models = {**store.models, model_id: updated_points}
    return (
        PriceHistoryStore(
            generated_at=recorded_at,
            models=updated_models,
        ),
        dirty,
    )


def load_model_history(model_id: str) -> list[PriceHistoryPoint]:
    path = model_history_path(model_id)
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    series = ModelHistorySeries.model_validate(payload)
    return series.points


def save_model_history(model_id: str, points: list[PriceHistoryPoint]) -> None:
    HISTORY_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    series = ModelHistorySeries(model_id=model_id, points=points)
    write_model_json(model_history_path(model_id), series)


def _load_legacy_history() -> PriceHistoryStore:
    payload = json.loads(LEGACY_HISTORY_PATH.read_text(encoding="utf-8"))
    return PriceHistoryStore.model_validate(payload)


def load_history_index() -> PriceHistoryIndex | None:
    if not HISTORY_INDEX_PATH.exists():
        return None
    payload = json.loads(HISTORY_INDEX_PATH.read_text(encoding="utf-8"))
    return PriceHistoryIndex.model_validate(payload)


def save_history_index(
    *,
    generated_at: datetime,
    model_ids: list[str],
) -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    index = PriceHistoryIndex(
        generated_at=generated_at,
        model_count=len(model_ids),
        models=sorted(model_ids),
    )
    write_model_json(HISTORY_INDEX_PATH, index)


def load_history() -> PriceHistoryStore:
    index = load_history_index()
    if index is not None:
        models: dict[str, list[PriceHistoryPoint]] = {}
        for model_id in index.models:
            models[model_id] = load_model_history(model_id)
        return PriceHistoryStore(generated_at=index.generated_at, models=models)
    if LEGACY_HISTORY_PATH.exists():
        return _load_legacy_history()
    now = datetime.now(UTC)
    return PriceHistoryStore(generated_at=now, models={})


def _prune_orphan_model_files(model_ids: set[str]) -> None:
    if not HISTORY_MODELS_DIR.exists():
        return
    keep_names = {f"{encode_model_id(model_id)}.json" for model_id in model_ids}
    for path in HISTORY_MODELS_DIR.glob("*.json"):
        if path.name not in keep_names:
            path.unlink()


def save_history(store: PriceHistoryStore) -> None:
    for model_id, points in store.models.items():
        save_model_history(model_id, points)
    model_ids = set(store.models.keys())
    _prune_orphan_model_files(model_ids)
    save_history_index(
        generated_at=store.generated_at,
        model_ids=list(model_ids),
    )


def save_dirty_history(
    store: PriceHistoryStore,
    *,
    dirty_model_ids: set[str],
    generated_at: datetime,
) -> None:
    for model_id in dirty_model_ids:
        points = store.models.get(model_id, [])
        if points:
            save_model_history(model_id, points)
    save_history_index(
        generated_at=generated_at,
        model_ids=list(store.models.keys()),
    )


def merge_build_into_history(
    snapshots: list[tuple[str, ModelPricing]],
    recorded_at: datetime,
) -> PriceHistoryStore:
    store = load_history()
    dirty_model_ids: set[str] = set()
    for model_id, pricing in snapshots:
        store, dirty = append_build_to_history(
            store,
            model_id=model_id,
            pricing=pricing,
            recorded_at=recorded_at,
        )
        if dirty:
            dirty_model_ids.add(model_id)
    if dirty_model_ids:
        save_dirty_history(
            store,
            dirty_model_ids=dirty_model_ids,
            generated_at=recorded_at,
        )
    return PriceHistoryStore(
        generated_at=recorded_at,
        models=store.models,
    )


def migrate_monolith_history_to_split() -> bool:
    if not LEGACY_HISTORY_PATH.exists():
        return False
    store = _load_legacy_history()
    cleaned_models: dict[str, list[PriceHistoryPoint]] = {}
    for model_id, points in store.models.items():
        cleaned = dedupe_consecutive_identical_points(points)
        if cleaned:
            cleaned_models[model_id] = cleaned
    migrated = PriceHistoryStore(
        generated_at=store.generated_at,
        models=cleaned_models,
    )
    save_history(migrated)
    LEGACY_HISTORY_PATH.unlink()
    return True


def repair_model_history_filenames() -> int:
    index = load_history_index()
    if index is None:
        return 0
    repaired = 0
    for model_id in index.models:
        correct = model_history_path(model_id)
        if correct.exists():
            continue
        broken_name = legacy_windows_broken_basename(model_id)
        if not broken_name:
            continue
        broken = HISTORY_MODELS_DIR / broken_name
        if not broken.exists():
            continue
        correct.parent.mkdir(parents=True, exist_ok=True)
        broken.rename(correct)
        repaired += 1
    return repaired
