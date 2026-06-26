from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from modelwatch.data_repair import (
    clean_alias_artifacts,
    clean_new_model_events_file,
    clean_price_drop_baselines,
    clean_price_events_file,
    clean_price_history,
    filter_new_model_events,
    filter_price_events,
    rebuild_price_drops_output,
    write_jsonl_events,
)
from modelwatch.history import (
    PriceHistoryPoint,
    PriceHistoryStore,
    load_history,
    save_history,
)
from modelwatch.json_output import dump_model_line
from modelwatch.price_baselines import load_baselines, save_baselines
from modelwatch.price_events import load_price_events
from modelwatch.schemas import (
    NewModelEventRecord,
    PriceDropBaselinesStore,
    PriceEventRecord,
)


def _zero_price_event(model_id: str) -> PriceEventRecord:
    return PriceEventRecord(
        detected_at=datetime(2026, 6, 25, 13, 30, tzinfo=UTC),
        model_id=model_id,
        field="prompt",
        old_per_million_usd="1.000000",
        new_per_million_usd="0.000000",
        pct_drop=1.0,
        saved_per_million_usd="1.000000",
    )


def _price_event(model_id: str) -> PriceEventRecord:
    return PriceEventRecord(
        detected_at=datetime(2026, 6, 25, 19, 0, tzinfo=UTC),
        model_id=model_id,
        field="prompt",
        old_per_million_usd="1.000000",
        new_per_million_usd="0.500000",
        pct_drop=0.5,
        saved_per_million_usd="0.500000",
    )


def _new_model_event(model_id: str) -> NewModelEventRecord:
    return NewModelEventRecord(
        detected_at=datetime(2026, 6, 9, 19, 30, tzinfo=UTC),
        model_id=model_id,
        name="Test",
        canonical_slug=model_id,
        created=1,
    )


def test_filter_price_events_removes_latest_aliases() -> None:
    events = [
        _price_event("moonshotai/kimi-k2.6"),
        _price_event("~moonshotai/kimi-latest"),
    ]
    filtered = filter_price_events(events)
    assert [event.model_id for event in filtered] == ["moonshotai/kimi-k2.6"]


def test_filter_new_model_events_removes_latest_aliases() -> None:
    events = [
        _new_model_event("anthropic/claude-fable-5"),
        _new_model_event("~anthropic/claude-fable-latest"),
    ]
    filtered = filter_new_model_events(events)
    assert [event.model_id for event in filtered] == ["anthropic/claude-fable-5"]


def test_filter_price_events_removes_spurious_zero_drops() -> None:
    events = [
        _price_event("moonshotai/kimi-k2.6"),
        _zero_price_event("moonshotai/kimi-k2.6"),
        _zero_price_event("cohere/north-mini-code:free"),
    ]
    filtered = filter_price_events(events)
    assert [event.model_id for event in filtered] == [
        "moonshotai/kimi-k2.6",
        "cohere/north-mini-code:free",
    ]


def test_clean_price_events_file_removes_aliases_and_rewrites(
    tmp_path: Path,
) -> None:
    path = tmp_path / "price-events.jsonl"
    events = [
        _price_event("moonshotai/kimi-k2.6"),
        _price_event("~moonshotai/kimi-latest"),
    ]
    write_jsonl_events(path, [dump_model_line(event) for event in events])

    removed = clean_price_events_file(path)

    assert removed == 1
    kept = load_price_events(path)
    assert [event.model_id for event in kept] == ["moonshotai/kimi-k2.6"]


def test_clean_new_model_events_file_removes_aliases(
    tmp_path: Path,
) -> None:
    path = tmp_path / "new-model-events.jsonl"
    events = [
        _new_model_event("anthropic/claude-fable-5"),
        _new_model_event("~anthropic/claude-fable-latest"),
    ]
    write_jsonl_events(path, [dump_model_line(event) for event in events])

    removed = clean_new_model_events_file(path)

    assert removed == 1
    from modelwatch.new_models import load_new_model_events

    kept = load_new_model_events(path)
    assert [event.model_id for event in kept] == ["anthropic/claude-fable-5"]


def test_clean_price_history_strips_glitch_points(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    history_path = tmp_path / "price-history.json"
    monkeypatch.setattr("modelwatch.history.HISTORY_PATH", history_path)
    at = datetime(2026, 6, 25, 13, 0, tzinfo=UTC)
    glitch = datetime(2026, 6, 25, 13, 30, tzinfo=UTC)
    recovered = datetime(2026, 6, 25, 14, 0, tzinfo=UTC)
    store = PriceHistoryStore(
        generated_at=at,
        models={
            "paid/model": [
                PriceHistoryPoint(
                    recorded_at=at,
                    prompt_per_million=Decimal("1"),
                ),
                PriceHistoryPoint(
                    recorded_at=glitch,
                    prompt_per_million=Decimal("0"),
                ),
                PriceHistoryPoint(
                    recorded_at=recovered,
                    prompt_per_million=Decimal("1"),
                ),
            ],
            "~vendor/model-latest": [
                PriceHistoryPoint(
                    recorded_at=at,
                    prompt_per_million=Decimal("1"),
                ),
            ],
        },
    )
    save_history(store)

    removed = clean_price_history()

    assert removed == 2
    cleaned = load_history()
    assert "~vendor/model-latest" not in cleaned.models
    assert len(cleaned.models["paid/model"]) == 2


def test_clean_price_drop_baselines_removes_aliases_and_zero_baselines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baselines_path = tmp_path / "price-drop-baselines.json"
    monkeypatch.setattr("modelwatch.price_baselines.BASELINES_PATH", baselines_path)
    at = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    store = PriceDropBaselinesStore(
        generated_at=at,
        models={
            "paid/model": {"prompt": "1.000000", "completion": "0.000000"},
            "~vendor/model-latest": {"prompt": "1.000000"},
        },
    )
    save_baselines(store)

    removed = clean_price_drop_baselines()

    assert removed == 2
    cleaned = load_baselines()
    assert "~vendor/model-latest" not in cleaned.models
    assert cleaned.models["paid/model"] == {"prompt": "1.000000"}


def test_rebuild_price_drops_output_writes_filtered_drops(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events_path = tmp_path / "price-events.jsonl"
    drops_path = tmp_path / "price-drops.json"
    monkeypatch.setattr("modelwatch.data_repair.EVENTS_PATH", events_path)
    now = datetime(2026, 6, 25, 20, 0, tzinfo=UTC)
    events = [
        _price_event("moonshotai/kimi-k2.6"),
        _price_event("~moonshotai/kimi-latest"),
    ]
    write_jsonl_events(events_path, [dump_model_line(event) for event in events])

    output = rebuild_price_drops_output(now=now, path=drops_path)

    assert len(output.drops) == 1
    assert output.drops[0].model_id == "moonshotai/kimi-k2.6"
    assert drops_path.exists()


def test_clean_alias_artifacts_runs_all_cleaners(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir = tmp_path / "data"
    snapshot_dir = tmp_path / "snapshots"
    data_dir.mkdir()
    snapshot_dir.mkdir()
    events_path = data_dir / "price-events.jsonl"
    new_events_path = data_dir / "new-model-events.jsonl"
    history_path = data_dir / "price-history.json"
    baselines_path = snapshot_dir / "price-drop-baselines.json"
    monkeypatch.setattr("modelwatch.data_repair.EVENTS_PATH", events_path)
    monkeypatch.setattr("modelwatch.data_repair.NEW_MODEL_EVENTS_PATH", new_events_path)
    monkeypatch.setattr("modelwatch.history.HISTORY_PATH", history_path)
    monkeypatch.setattr("modelwatch.price_baselines.BASELINES_PATH", baselines_path)
    write_jsonl_events(
        events_path,
        [dump_model_line(_price_event("~moonshotai/kimi-latest"))],
    )
    write_jsonl_events(
        new_events_path,
        [dump_model_line(_new_model_event("~anthropic/claude-fable-latest"))],
    )

    counts = clean_alias_artifacts()

    assert counts["price_events_removed"] == 1
    assert counts["new_model_events_removed"] == 1
