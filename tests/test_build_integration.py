import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from modelwatch.build import _comparison_basis_changed, run_build
from modelwatch.history import (
    PriceHistoryPoint,
    save_history_index,
    save_model_history,
)
from modelwatch.pricing_schedule import pricing_schedule_from_raw
from modelwatch.schemas import (
    BuildMeta,
    ModelArchitecture,
    ModelPricing,
    ModelSnapshot,
    ModelsOutput,
    NewModelsOutput,
    PreviousSnapshot,
    PriceChangesOutput,
    TopProviderInfo,
)

DEEPSEEK_ID = "deepseek/deepseek-v4.1-flash"
OFF_PEAK = ("0.00000015", "0.0000006")
PEAK = ("0.0000003", "0.0000012")


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
    monkeypatch.setattr(
        "modelwatch.build.EVENTS_PATH", data_dir / "price-change-events.jsonl"
    )
    monkeypatch.setattr(
        "modelwatch.build.NEW_MODEL_EVENTS_PATH",
        data_dir / "new-model-events.jsonl",
    )
    monkeypatch.setattr("modelwatch.history.HISTORY_DIR", data_dir / "price-history")
    monkeypatch.setattr(
        "modelwatch.history.HISTORY_INDEX_PATH",
        data_dir / "price-history" / "index.json",
    )
    monkeypatch.setattr(
        "modelwatch.history.HISTORY_MODELS_DIR",
        data_dir / "price-history" / "models",
    )
    monkeypatch.setattr(
        "modelwatch.history.LEGACY_HISTORY_PATH",
        data_dir / "price-history.json",
    )
    monkeypatch.setattr(
        "modelwatch.price_change_state.STATE_PATH",
        snapshot_dir / "price-change-state.json",
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
    changes_output = PriceChangesOutput.model_validate_json(
        (build_paths / "price-changes.json").read_text(encoding="utf-8"),
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
    assert changes_output.active_changes == []
    assert changes_output.recovered_changes == []
    assert changes_output.episodes == []
    assert new_models_output.models == []
    assert model.id in previous.models
    assert json.loads(
        (build_paths / "models.json").read_text(encoding="utf-8")
    ) == json.loads(
        (build_paths / "models.json").read_text(encoding="utf-8"),
    )


def _snapshot_with_schedule(*, with_schedule: bool) -> ModelSnapshot:
    snapshot = _minimal_snapshot()
    if not with_schedule:
        return snapshot
    schedule = pricing_schedule_from_raw(
        {
            "prompt": "0.000001",
            "completion": "0.000002",
            "overrides": [
                {
                    "utc_start": 100,
                    "utc_end": 400,
                    "prompt": "0.000002",
                    "completion": "0.000004",
                },
            ],
        },
    )
    assert schedule is not None
    return snapshot.model_copy(update={"pricing_schedule": schedule})


def _previous_with(snapshot: ModelSnapshot | None) -> PreviousSnapshot:
    models = {} if snapshot is None else {snapshot.id: snapshot}
    return PreviousSnapshot(
        generated_at=datetime(2026, 9, 21, 12, 0, tzinfo=UTC),
        models=models,
    )


def test_comparison_basis_unchanged_when_both_sides_agree() -> None:
    scheduled = _snapshot_with_schedule(with_schedule=True)
    plain = _snapshot_with_schedule(with_schedule=False)

    assert not _comparison_basis_changed(_previous_with(scheduled), scheduled)
    assert not _comparison_basis_changed(_previous_with(plain), plain)
    assert not _comparison_basis_changed(None, scheduled)
    assert not _comparison_basis_changed(_previous_with(None), scheduled)


def test_comparison_basis_changes_when_schedule_appears_or_disappears() -> None:
    scheduled = _snapshot_with_schedule(with_schedule=True)
    plain = _snapshot_with_schedule(with_schedule=False)

    assert _comparison_basis_changed(_previous_with(plain), scheduled)
    assert _comparison_basis_changed(_previous_with(scheduled), plain)


def _scheduled_raw_model(
    *,
    active: tuple[str, str],
    peak: tuple[str, str] = PEAK,
) -> dict[str, object]:
    """Raw models-API entry for a model with a weekday peak/off-peak schedule.

    ``active`` is the price OpenRouter reports at fetch time, i.e. whichever
    window is in effect right now.
    """
    off_prompt, off_completion = OFF_PEAK
    peak_prompt, peak_completion = peak
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    return {
        "id": DEEPSEEK_ID,
        "canonical_slug": "deepseek/deepseek-v4.1-flash-20260910",
        "name": "DeepSeek: DeepSeek V4.1 Flash",
        "created": 1,
        "architecture": {
            "input_modalities": ["text"],
            "output_modalities": ["text"],
        },
        "pricing": {
            "prompt": active[0],
            "completion": active[1],
            "overrides": [
                {
                    "utc_days": weekdays,
                    "utc_start": 100,
                    "utc_end": 400,
                    "prompt": peak_prompt,
                    "completion": peak_completion,
                },
                {
                    "utc_days": weekdays,
                    "utc_start": 1000,
                    "utc_end": 0,
                    "prompt": off_prompt,
                    "completion": off_completion,
                },
            ],
        },
        "top_provider": {"context_length": 1048576, "is_moderated": False},
        "supported_parameters": ["temperature"],
    }


def _run_build_once(raw_model: dict[str, object]) -> None:
    benchmark_payload = [
        {
            "canonical_slug": raw_model["canonical_slug"],
            "design_arena_error": "unavailable",
            "artificial_analysis_error": "unavailable",
            "benchmark_scores_error": "unavailable",
            "effective_pricing_error": "unavailable",
        }
    ]
    endpoints_payload = [
        {"model_id": raw_model["id"], "endpoints_error": "unavailable"}
    ]
    with (
        patch(
            "modelwatch.build.fetch_models_async",
            new=AsyncMock(return_value=[raw_model]),
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


def _seed_flapping_history() -> None:
    """History as recorded before schedules were understood: peak/off-peak mix."""
    now = datetime.now(UTC)
    points = [
        PriceHistoryPoint(
            recorded_at=now - timedelta(days=2),
            prompt_per_million=Decimal("0.15"),
            completion_per_million=Decimal("0.6"),
        ),
        PriceHistoryPoint(
            recorded_at=now - timedelta(days=1),
            prompt_per_million=Decimal("0.3"),
            completion_per_million=Decimal("1.2"),
        ),
        PriceHistoryPoint(
            recorded_at=now - timedelta(hours=1),
            prompt_per_million=Decimal("0.15"),
            completion_per_million=Decimal("0.6"),
        ),
    ]
    save_model_history(DEEPSEEK_ID, points)
    save_history_index(generated_at=now, model_ids=[DEEPSEEK_ID])


def test_window_flip_does_not_report_a_price_change(
    build_paths: Path,
) -> None:
    """Entering the peak window is not a price change; a real hike still is."""
    _seed_flapping_history()

    _run_build_once(_scheduled_raw_model(active=OFF_PEAK))
    changes = PriceChangesOutput.model_validate_json(
        (build_paths / "price-changes.json").read_text(encoding="utf-8"),
    )
    assert changes.episodes == []
    assert changes.active_changes == []

    # Same rate card, but OpenRouter now reports the peak window price.
    _run_build_once(_scheduled_raw_model(active=PEAK))
    changes = PriceChangesOutput.model_validate_json(
        (build_paths / "price-changes.json").read_text(encoding="utf-8"),
    )
    assert changes.episodes == []
    assert changes.active_changes == []

    # The history chart tracks the standard rate, so the flip appends nothing.
    history_payload = json.loads(
        (
            build_paths
            / "price-history"
            / "models"
            / "deepseek__deepseek-v4.1-flash.json"
        ).read_text(encoding="utf-8"),
    )
    points = history_payload["points"]
    assert Decimal(points[-1]["prompt_per_million"]) == Decimal("0.3")
    assert len(points) == 4


def test_standard_rate_change_is_still_reported(
    build_paths: Path,
) -> None:
    _seed_flapping_history()

    _run_build_once(_scheduled_raw_model(active=OFF_PEAK))
    # The provider raises its peak rate; off-peak stays where it was.
    raised_peak = ("0.00000045", "0.0000018")
    _run_build_once(_scheduled_raw_model(active=raised_peak, peak=raised_peak))
    changes = PriceChangesOutput.model_validate_json(
        (build_paths / "price-changes.json").read_text(encoding="utf-8"),
    )
    assert changes.episodes == []

    _run_build_once(_scheduled_raw_model(active=raised_peak, peak=raised_peak))
    changes = PriceChangesOutput.model_validate_json(
        (build_paths / "price-changes.json").read_text(encoding="utf-8"),
    )
    prompt_episodes = [
        episode for episode in changes.episodes if episode.field == "prompt"
    ]
    assert len(prompt_episodes) == 1
    episode = prompt_episodes[0]
    assert episode.direction == "hike"
    assert episode.old_per_million_usd == "0.300000"
    assert episode.new_per_million_usd == "0.450000"
    assert episode.status == "active"
    assert {change.field for change in changes.active_changes} == {
        "prompt",
        "completion",
    }


def test_off_peak_only_change_is_reported_as_an_off_peak_change(
    build_paths: Path,
) -> None:
    """A deeper discount moves the off-peak track, not the standard rate."""
    _seed_flapping_history()

    _run_build_once(_scheduled_raw_model(active=OFF_PEAK))
    deeper_discount = ("0.0000001", "0.0000004")
    _run_build_once(_scheduled_raw_model(active=deeper_discount))
    changes = PriceChangesOutput.model_validate_json(
        (build_paths / "price-changes.json").read_text(encoding="utf-8"),
    )
    assert changes.episodes == []

    _run_build_once(_scheduled_raw_model(active=deeper_discount))
    changes = PriceChangesOutput.model_validate_json(
        (build_paths / "price-changes.json").read_text(encoding="utf-8"),
    )
    off_peak_episodes = [
        episode
        for episode in changes.episodes
        if episode.field == "prompt" and episode.tier == "offpeak"
    ]
    assert len(off_peak_episodes) == 1
    episode = off_peak_episodes[0]
    assert episode.direction == "cut"
    assert episode.old_per_million_usd == "0.150000"
    assert episode.new_per_million_usd == "0.100000"
    assert episode.status == "active"

    models_output = ModelsOutput.model_validate_json(
        (build_paths / "models.json").read_text(encoding="utf-8"),
    )
    schedule = models_output.models[0].model.pricing_schedule
    assert schedule is not None
    assert schedule.standard["prompt"] == "0.0000003"
    assert schedule.minimum["prompt"] == "0.0000001"
