from modelwatch.schemas import (
    BenchmarkFetchStatus,
    DesignArenaBenchmarks,
    EnrichedModel,
    ModelArchitecture,
    ModelBenchmarks,
    ModelPricing,
    ModelSnapshot,
    TopProviderInfo,
)
from modelwatch.stable_output import stabilize_enriched_models


def _minimal_model(*, model_id: str = "zeta/model") -> ModelSnapshot:
    return ModelSnapshot(
        id=model_id,
        canonical_slug=model_id,
        name="Zeta",
        created=1,
        architecture=ModelArchitecture(
            input_modalities=["text"],
            output_modalities=["text"],
        ),
        pricing=ModelPricing(prompt="0.000001", completion="0.000002"),
        top_provider=TopProviderInfo(is_moderated=False),
        supported_parameters=["temperature", "max_tokens"],
    )


def _design_record(*, arena: str, category: str) -> dict[str, object]:
    return {
        "arena": arena,
        "category": category,
        "da_model_id": "demo",
        "elo": 1200,
    }


def test_stabilize_enriched_models_sorts_by_model_id() -> None:
    alpha = EnrichedModel(
        model=_minimal_model(model_id="alpha/model"),
        benchmarks=ModelBenchmarks(
            design_arena_status=BenchmarkFetchStatus(status="empty"),
            artificial_analysis=[],
            artificial_analysis_status=BenchmarkFetchStatus(status="empty"),
        ),
    )
    zeta = EnrichedModel(
        model=_minimal_model(model_id="zeta/model"),
        benchmarks=ModelBenchmarks(
            design_arena_status=BenchmarkFetchStatus(status="empty"),
            artificial_analysis=[],
            artificial_analysis_status=BenchmarkFetchStatus(status="empty"),
        ),
    )

    stabilized = stabilize_enriched_models([zeta, alpha])

    assert [entry.model.id for entry in stabilized] == ["alpha/model", "zeta/model"]


def test_stabilize_enriched_models_sorts_design_arena_records() -> None:
    benchmarks = ModelBenchmarks(
        design_arena=DesignArenaBenchmarks(
            records=[
                _design_record(arena="Models Arena", category="UI Component"),
                _design_record(arena="Agents Arena", category="Agentic Game Dev"),
            ],
        ),
        design_arena_status=BenchmarkFetchStatus(status="ok"),
        artificial_analysis=[],
        artificial_analysis_status=BenchmarkFetchStatus(status="empty"),
    )
    enriched = EnrichedModel(model=_minimal_model(), benchmarks=benchmarks)

    stabilized = stabilize_enriched_models([enriched])[0]
    records = stabilized.benchmarks.design_arena
    assert records is not None
    assert [str(record["arena"]) for record in records.records] == [
        "Agents Arena",
        "Models Arena",
    ]


def test_stabilize_enriched_models_sorts_supported_parameters() -> None:
    enriched = EnrichedModel(
        model=_minimal_model(),
        benchmarks=ModelBenchmarks(
            design_arena_status=BenchmarkFetchStatus(status="empty"),
            artificial_analysis=[],
            artificial_analysis_status=BenchmarkFetchStatus(status="empty"),
        ),
    )

    stabilized = stabilize_enriched_models([enriched])[0]

    assert stabilized.model.supported_parameters == ["max_tokens", "temperature"]
