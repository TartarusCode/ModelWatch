from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from modelwatch.history import (
    ModelHistorySeries,
    PriceHistoryPoint,
    PriceHistoryStore,
    append_build_to_history,
    decode_model_id,
    dedupe_consecutive_identical_points,
    encode_model_id,
    load_history,
    load_model_history,
    merge_build_into_history,
    migrate_monolith_history_to_split,
    model_history_path,
    pricing_to_history_fields,
    repair_model_history_filenames,
    save_history,
    save_history_index,
)
from modelwatch.json_output import write_model_json
from modelwatch.schemas import ModelPricing


@pytest.fixture
def history_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    history_root = tmp_path / "price-history"
    monkeypatch.setattr("modelwatch.history.HISTORY_DIR", history_root)
    monkeypatch.setattr(
        "modelwatch.history.HISTORY_INDEX_PATH", history_root / "index.json"
    )
    monkeypatch.setattr(
        "modelwatch.history.HISTORY_MODELS_DIR", history_root / "models"
    )
    monkeypatch.setattr(
        "modelwatch.history.LEGACY_HISTORY_PATH", tmp_path / "price-history.json"
    )
    return history_root


def test_pricing_to_history_fields_converts_tokens() -> None:
    pricing = ModelPricing(prompt="0.000003", completion="0.000015")
    fields = pricing_to_history_fields(pricing)
    assert fields["prompt"] == Decimal("3")
    assert fields["completion"] == Decimal("15")


def test_pricing_to_history_fields_marks_variable_as_none() -> None:
    pricing = ModelPricing(prompt="-1", completion="-1")
    fields = pricing_to_history_fields(pricing)
    assert fields["prompt"] is None
    assert fields["completion"] is None


def test_encode_model_id_replaces_slashes_and_colons() -> None:
    assert encode_model_id("openai/gpt-4o") == "openai__gpt-4o"
    assert (
        encode_model_id("cohere/north-mini-code:free")
        == "cohere__north-mini-code_colon_free"
    )


def test_decode_model_id_round_trip() -> None:
    model_id = "deepseek/deepseek-v4-flash:free"
    assert decode_model_id(encode_model_id(model_id)) == model_id


def test_model_history_path_uses_encoded_name(history_dir: Path) -> None:
    path = model_history_path("openai/gpt-4o")
    assert path == history_dir / "models" / "openai__gpt-4o.json"


def test_append_build_adds_point_per_model() -> None:
    at = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    store = PriceHistoryStore(generated_at=at, models={})
    pricing = ModelPricing(prompt="0.000002", completion="0.000010")
    updated, dirty = append_build_to_history(
        store,
        model_id="acme/model",
        pricing=pricing,
        recorded_at=at,
    )
    assert dirty is True
    assert "acme/model" in updated.models
    assert len(updated.models["acme/model"]) == 1


def test_append_build_skips_unchanged_within_heartbeat_window() -> None:
    at = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    pricing = ModelPricing(prompt="0.000002", completion="0.000010")
    point = PriceHistoryPoint(
        recorded_at=at,
        prompt_per_million=Decimal("2"),
        completion_per_million=Decimal("10"),
    )
    store = PriceHistoryStore(
        generated_at=at,
        models={"acme/model": [point]},
    )
    later = datetime(2026, 5, 29, 12, 30, tzinfo=UTC)
    updated, dirty = append_build_to_history(
        store,
        model_id="acme/model",
        pricing=pricing,
        recorded_at=later,
    )
    assert dirty is False
    assert len(updated.models["acme/model"]) == 1


def test_append_build_heartbeats_unchanged_after_24h() -> None:
    at = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    pricing = ModelPricing(prompt="0.000002", completion="0.000010")
    point = PriceHistoryPoint(
        recorded_at=at,
        prompt_per_million=Decimal("2"),
        completion_per_million=Decimal("10"),
    )
    store = PriceHistoryStore(
        generated_at=at,
        models={"acme/model": [point]},
    )
    later = datetime(2026, 5, 30, 12, 0, tzinfo=UTC)
    updated, dirty = append_build_to_history(
        store,
        model_id="acme/model",
        pricing=pricing,
        recorded_at=later,
    )
    assert dirty is True
    assert len(updated.models["acme/model"]) == 2
    assert updated.models["acme/model"][-1].recorded_at == later


def test_append_build_records_cache_read_in_history() -> None:
    at = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    store = PriceHistoryStore(generated_at=at, models={})
    pricing = ModelPricing(
        prompt="0.000002",
        completion="0.000010",
        input_cache_read="0.0000005",
    )
    updated, dirty = append_build_to_history(
        store,
        model_id="acme/model",
        pricing=pricing,
        recorded_at=at,
    )
    assert dirty is True
    point = updated.models["acme/model"][0]
    assert point.input_cache_read_per_million == Decimal("0.5")


def test_append_build_records_price_change() -> None:
    at = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    point = PriceHistoryPoint(
        recorded_at=at,
        prompt_per_million=Decimal("2"),
        completion_per_million=Decimal("10"),
    )
    store = PriceHistoryStore(
        generated_at=at,
        models={"acme/model": [point]},
    )
    later = datetime(2026, 5, 29, 12, 30, tzinfo=UTC)
    new_pricing = ModelPricing(prompt="0.000001", completion="0.000010")
    updated, dirty = append_build_to_history(
        store,
        model_id="acme/model",
        pricing=new_pricing,
        recorded_at=later,
    )
    assert dirty is True
    assert len(updated.models["acme/model"]) == 2


def test_load_and_save_split_history_round_trip(history_dir: Path) -> None:
    at = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    store = PriceHistoryStore(
        generated_at=at,
        models={
            "acme/model": [
                PriceHistoryPoint(
                    recorded_at=at,
                    prompt_per_million=Decimal("3"),
                ),
            ],
        },
    )

    save_history(store)
    loaded = load_history()

    assert loaded.models["acme/model"][0].prompt_per_million == Decimal("3")
    assert (history_dir / "index.json").exists()
    assert model_history_path("acme/model").exists()


def test_merge_build_into_history_writes_only_dirty_models(
    history_dir: Path,
) -> None:
    at = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    unchanged_pricing = ModelPricing(prompt="0.000002", completion="0.000010")
    save_history(
        PriceHistoryStore(
            generated_at=at,
            models={
                "acme/stable": [
                    PriceHistoryPoint(
                        recorded_at=at,
                        prompt_per_million=Decimal("2"),
                        completion_per_million=Decimal("10"),
                    ),
                ],
            },
        ),
    )
    later = datetime(2026, 6, 25, 12, 30, tzinfo=UTC)
    stable_mtime_before = model_history_path("acme/stable").stat().st_mtime

    merge_build_into_history(
        [
            ("acme/stable", unchanged_pricing),
            ("acme/new", unchanged_pricing),
        ],
        recorded_at=later,
    )

    assert model_history_path("acme/stable").stat().st_mtime == stable_mtime_before
    assert model_history_path("acme/new").exists()


def test_dedupe_consecutive_identical_points() -> None:
    at = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    later = datetime(2026, 6, 25, 13, 0, tzinfo=UTC)
    points = [
        PriceHistoryPoint(
            recorded_at=at,
            prompt_per_million=Decimal("2"),
            completion_per_million=Decimal("10"),
        ),
        PriceHistoryPoint(
            recorded_at=later,
            prompt_per_million=Decimal("2"),
            completion_per_million=Decimal("10"),
        ),
        PriceHistoryPoint(
            recorded_at=later + timedelta(hours=1),
            prompt_per_million=Decimal("1"),
            completion_per_million=Decimal("10"),
        ),
    ]

    deduped = dedupe_consecutive_identical_points(points)

    assert len(deduped) == 2
    assert deduped[0].recorded_at == at
    assert deduped[1].prompt_per_million == Decimal("1")


def test_load_model_history_returns_empty_for_missing_file(history_dir: Path) -> None:
    assert load_model_history("missing/model") == []


def test_load_model_history_returns_empty_for_empty_file(history_dir: Path) -> None:
    path = model_history_path("acme/empty:free")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    assert load_model_history("acme/empty:free") == []


def test_repair_model_history_filenames_moves_colon_broken_paths(
    history_dir: Path,
) -> None:
    at = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    model_id = "cohere/north-mini-code:free"
    broken = history_dir / "models" / "cohere__north-mini-code"
    broken.parent.mkdir(parents=True, exist_ok=True)
    write_model_json(
        broken,
        ModelHistorySeries(model_id=model_id, points=[]),
    )
    save_history_index(
        generated_at=at,
        model_ids=[model_id],
    )

    repaired = repair_model_history_filenames()

    assert repaired == 1
    assert model_history_path(model_id).exists()
    assert not broken.exists()


def test_migrate_monolith_history_to_split(
    history_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy = tmp_path / "price-history.json"
    at = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    legacy.write_text(
        PriceHistoryStore(
            generated_at=at,
            models={
                "acme/model": [
                    PriceHistoryPoint(
                        recorded_at=at,
                        prompt_per_million=Decimal("3"),
                    ),
                ],
            },
        ).model_dump_json(),
        encoding="utf-8",
    )
    monkeypatch.setattr("modelwatch.history.LEGACY_HISTORY_PATH", legacy)

    migrated = migrate_monolith_history_to_split()

    assert migrated is True
    assert not legacy.exists()
    loaded = load_history()
    assert loaded.models["acme/model"][0].prompt_per_million == Decimal("3")
