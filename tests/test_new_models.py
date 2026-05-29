from datetime import UTC, datetime, timedelta
from pathlib import Path

from modelwatch.new_models import (
    NEW_MODEL_LOOKBACK_HOURS,
    detect_new_models,
    events_in_last_hours,
    load_new_model_events,
    models_in_last_hours,
    records_from_events,
)
from modelwatch.schemas import ModelSnapshot, NewModelEventRecord, PreviousSnapshot


def _minimal_snapshot(
    *,
    model_id: str = "acme/widget",
    name: str = "Widget",
    created: int = 1_700_000_000,
) -> ModelSnapshot:
    return ModelSnapshot.model_validate(
        {
            "id": model_id,
            "canonical_slug": "acme/widget",
            "name": name,
            "created": created,
            "description": None,
            "context_length": 8192,
            "architecture": {
                "input_modalities": ["text"],
                "output_modalities": ["text"],
            },
            "pricing": {"prompt": "0.000001", "completion": "0.000002"},
            "top_provider": {"is_moderated": False},
            "supported_parameters": [],
        },
    )


def _event(
    *,
    detected_at: datetime,
    model_id: str = "acme/new-one",
) -> NewModelEventRecord:
    return NewModelEventRecord(
        detected_at=detected_at,
        model_id=model_id,
        name="New One",
        canonical_slug="acme/new-one",
        created=1_700_000_000,
    )


def test_detect_new_models_returns_ids_missing_from_previous() -> None:
    previous = PreviousSnapshot(
        generated_at=datetime(2026, 5, 28, tzinfo=UTC),
        models={"acme/old": _minimal_snapshot(model_id="acme/old")},
    )
    current = [
        _minimal_snapshot(model_id="acme/old"),
        _minimal_snapshot(model_id="acme/brand-new", name="Brand New"),
    ]

    additions = detect_new_models(current, previous=previous)

    assert len(additions) == 1
    assert additions[0].model_id == "acme/brand-new"
    assert additions[0].name == "Brand New"


def test_detect_new_models_returns_empty_without_previous() -> None:
    current = [_minimal_snapshot()]

    assert detect_new_models(current, previous=None) == []


def test_events_in_last_hours_includes_recent_only() -> None:
    now = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    events = [
        _event(detected_at=now - timedelta(hours=1)),
        _event(detected_at=now - timedelta(hours=25)),
        _event(detected_at=now - timedelta(hours=23)),
    ]

    filtered = events_in_last_hours(events, NEW_MODEL_LOOKBACK_HOURS, now=now)

    assert len(filtered) == 2


def test_records_from_events_maps_fields() -> None:
    at = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    event = _event(detected_at=at, model_id="vendor/model-x")

    records = records_from_events([event])

    assert len(records) == 1
    assert records[0].detected_at == at
    assert records[0].model_id == "vendor/model-x"
    assert records[0].canonical_slug == "acme/new-one"


def test_models_in_last_hours_sorts_newest_first() -> None:
    now = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    older = _event(detected_at=now - timedelta(hours=2), model_id="a/one")
    newer = _event(detected_at=now - timedelta(hours=1), model_id="b/two")

    records = models_in_last_hours([older, newer], NEW_MODEL_LOOKBACK_HOURS, now=now)

    assert [record.model_id for record in records] == ["b/two", "a/one"]


def test_load_new_model_events_reads_jsonl(tmp_path: object) -> None:
    path = Path(str(tmp_path)) / "events.jsonl"
    at = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    event = _event(detected_at=at)
    path.write_text(event.model_dump_json() + "\n", encoding="utf-8")

    loaded = load_new_model_events(path)

    assert len(loaded) == 1
    assert loaded[0].model_id == "acme/new-one"
