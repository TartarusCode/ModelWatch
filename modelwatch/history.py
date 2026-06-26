from datetime import UTC, datetime
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

HISTORY_PATH = (
    Path(__file__).resolve().parent.parent
    / "web"
    / "public"
    / "data"
    / "price-history.json"
)
MAX_POINTS_PER_MODEL = 500


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


class PriceHistoryStore(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    models: dict[str, list[PriceHistoryPoint]]


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


def append_build_to_history(
    store: PriceHistoryStore,
    model_id: str,
    pricing: ModelPricing,
    recorded_at: datetime,
) -> PriceHistoryStore:
    existing = list(store.models.get(model_id, []))
    fields = sanitize_history_fields(
        model_id,
        pricing_to_history_fields(pricing),
        existing,
    )
    if not has_recordable_history_fields(fields):
        return store
    point = PriceHistoryPoint(
        recorded_at=recorded_at,
        **{
            per_million_field_name(field): fields.get(field) for field in PRICING_FIELDS
        },
    )
    updated_points = [*existing, point][-MAX_POINTS_PER_MODEL:]
    updated_models = {**store.models, model_id: updated_points}
    return PriceHistoryStore(
        generated_at=recorded_at,
        models=updated_models,
    )


def load_history() -> PriceHistoryStore:
    if not HISTORY_PATH.exists():
        now = datetime.now(UTC)
        return PriceHistoryStore(generated_at=now, models={})
    import json

    payload = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    return PriceHistoryStore.model_validate(payload)


def save_history(store: PriceHistoryStore) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_model_json(HISTORY_PATH, store)


def merge_build_into_history(
    snapshots: list[tuple[str, ModelPricing]],
    recorded_at: datetime,
) -> PriceHistoryStore:
    store = load_history()
    for model_id, pricing in snapshots:
        store = append_build_to_history(
            store,
            model_id=model_id,
            pricing=pricing,
            recorded_at=recorded_at,
        )
    return PriceHistoryStore(
        generated_at=recorded_at,
        models=store.models,
    )
