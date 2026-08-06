import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict

from modelwatch.aa_scores import summarize_artificial_analysis
from modelwatch.benchmark_health import probes_indicate_broken_endpoints
from modelwatch.history import (
    PriceHistoryPoint,
    PriceHistoryStore,
    load_history,
    merge_build_into_history,
    save_history,
)
from modelwatch.json_output import write_model_json
from modelwatch.new_models import models_in_last_hours
from modelwatch.schemas import (
    ModelPricing,
    NewModelEventRecord,
)


class _SampleModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    zebra: str
    alpha: int


def _aa_record(
    *,
    aa_slug: str,
    aa_name: str,
    intelligence: float,
    coding: float,
    agentic: float,
    heuristic_openrouter_slug: str | None = None,
) -> dict[str, object]:
    return {
        "aa_slug": aa_slug,
        "aa_name": aa_name,
        "heuristic_openrouter_slug": heuristic_openrouter_slug,
        "benchmark_data": {
            "evaluations": {
                "artificial_analysis_intelligence_index": intelligence,
                "artificial_analysis_coding_index": coding,
                "artificial_analysis_agentic_index": agentic,
            },
        },
        "percentiles": {
            "intelligence_percentile": 80,
            "coding_percentile": 75,
            "agentic_percentile": 70,
        },
    }


def test_load_and_save_history_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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


def test_merge_build_into_history_appends_points(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    at = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    pricing = ModelPricing(prompt="0.000002", completion="0.000010")

    merged = merge_build_into_history([("acme/model", pricing)], recorded_at=at)
    save_history(merged)
    loaded = load_history()

    assert len(loaded.models["acme/model"]) == 1


def test_write_model_json_writes_sorted_keys(tmp_path: Path) -> None:
    path = tmp_path / "sample.json"
    model = _SampleModel(zebra="z", alpha=1)

    write_model_json(path, model)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert list(payload.keys()) == ["alpha", "zebra"]


def test_models_in_last_hours_filters_latest_aliases() -> None:
    now = datetime(2026, 6, 25, 20, 0, tzinfo=UTC)
    events = [
        NewModelEventRecord(
            detected_at=now - timedelta(hours=1),
            model_id="anthropic/claude-fable-5",
            name="Claude",
            canonical_slug="anthropic/claude-fable-5",
            created=1,
        ),
        NewModelEventRecord(
            detected_at=now - timedelta(hours=1),
            model_id="~anthropic/claude-fable-latest",
            name="Latest",
            canonical_slug="anthropic/claude-fable-latest",
            created=1,
        ),
    ]

    records = models_in_last_hours(events, 24, now=now)

    assert [record.model_id for record in records] == ["anthropic/claude-fable-5"]


def test_probes_indicate_broken_when_results_empty() -> None:
    assert probes_indicate_broken_endpoints([]) is True


def test_summarize_artificial_analysis_returns_summary() -> None:
    records = [
        _aa_record(
            aa_slug="model",
            aa_name="Model (Max Effort)",
            intelligence=46.5,
            coding=38.7,
            agentic=61.3,
            heuristic_openrouter_slug="vendor/model",
        ),
    ]

    summary = summarize_artificial_analysis(records, model_id="vendor/model")

    assert summary is not None
    assert summary.intelligence_index == 46.5
    assert summary.aa_slug == "model"
