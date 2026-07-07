import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from modelwatch.build import run_build
from modelwatch.schemas import (
    BuildMeta,
    ModelArchitecture,
    ModelPricing,
    ModelSnapshot,
    ModelsOutput,
    NewModelsOutput,
    PreviousSnapshot,
    PriceDropsOutput,
    TopProviderInfo,
)


def _minimal_snapshot(*, model_id: str = "acme/demo") -> ModelSnapshot:
    return ModelSnapshot(
        id=model_id,
        canonical_slug=model_id,
        name="Demo",
        created=1,
        architecture=ModelArchitecture(
            input_modalities=["text"],
            output_modalities=["text"],
        ),
        pricing=ModelPricing(prompt="0.000001", completion="0.000002"),
        top_provider=TopProviderInfo(is_moderated=False),
        supported_parameters=["temperature"],
    )


def _raw_model(snapshot: ModelSnapshot) -> dict[str, object]:
    return snapshot.model_dump(mode="json")


@pytest.fixture
def build_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data_dir = tmp_path / "web" / "public" / "data"
    snapshot_dir = tmp_path / "data" / "snapshots"
    data_dir.mkdir(parents=True)
    snapshot_dir.mkdir(parents=True)

    monkeypatch.setattr("modelwatch.build.DATA_DIR", data_dir)
    monkeypatch.setattr(
        "modelwatch.build.SNAPSHOT_PATH", snapshot_dir / "previous.json"
    )
    monkeypatch.setattr("modelwatch.build.EVENTS_PATH", data_dir / "price-events.jsonl")
    monkeypatch.setattr(
        "modelwatch.build.NEW_MODEL_EVENTS_PATH",
        data_dir / "new-model-events.jsonl",
    )
    monkeypatch.setattr(
        "modelwatch.history.HISTORY_PATH", data_dir / "price-history.json"
    )
    monkeypatch.setattr(
        "modelwatch.price_drop_state.STATE_PATH",
        snapshot_dir / "price-drop-state.json",
    )
    return data_dir


def test_run_build_writes_stable_json_artifacts(build_paths: Path) -> None:
    model = _minimal_snapshot()
    benchmark_payload = [
        {
            "canonical_slug": model.canonical_slug,
            "design_arena_error": "unavailable",
            "artificial_analysis_error": "unavailable",
            "benchmark_scores_error": "unavailable",
            "effective_pricing_error": "unavailable",
        }
    ]
    endpoints_payload = [
        {
            "model_id": model.id,
            "endpoints_error": "unavailable",
        }
    ]

    with (
        patch(
            "modelwatch.build.fetch_models_async",
            new=AsyncMock(return_value=[_raw_model(model)]),
        ),
        patch(
            "modelwatch.build.fetch_all_benchmarks",
            new=AsyncMock(return_value=benchmark_payload),
        ),
        patch(
            "modelwatch.build.fetch_all_provider_endpoints",
            new=AsyncMock(return_value=endpoints_payload),
        ),
    ):
        import asyncio

        asyncio.run(run_build())

    models_output = ModelsOutput.model_validate_json(
        (build_paths / "models.json").read_text(encoding="utf-8"),
    )
    drops_output = PriceDropsOutput.model_validate_json(
        (build_paths / "price-drops.json").read_text(encoding="utf-8"),
    )
    new_models_output = NewModelsOutput.model_validate_json(
        (build_paths / "new-models.json").read_text(encoding="utf-8"),
    )
    meta = BuildMeta.model_validate_json(
        (build_paths / "meta.json").read_text(encoding="utf-8"),
    )
    previous = PreviousSnapshot.model_validate_json(
        (
            build_paths.parent.parent.parent / "data" / "snapshots" / "previous.json"
        ).read_text(
            encoding="utf-8",
        ),
    )

    assert len(models_output.models) == 1
    assert models_output.models[0].model.id == model.id
    assert meta.model_count == 1
    assert meta.benchmark_errors >= 1
    assert drops_output.active_drops == []
    assert drops_output.recovered_drops == []
    assert drops_output.episodes == []
    assert new_models_output.models == []
    assert model.id in previous.models
    assert json.loads(
        (build_paths / "models.json").read_text(encoding="utf-8")
    ) == json.loads(
        (build_paths / "models.json").read_text(encoding="utf-8"),
    )
