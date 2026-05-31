from collections.abc import Callable

from modelwatch.schemas import (
    DesignArenaBenchmarks,
    EnrichedModel,
    ModelBenchmarks,
    ModelSnapshot,
)


def _design_arena_record_key(record: dict[str, object]) -> tuple[str, str, str]:
    model_ref = record.get("da_model_id") or record.get("openrouter_id") or ""
    return (
        str(record.get("arena") or ""),
        str(record.get("category") or ""),
        str(model_ref),
    )


def _aa_record_key(record: dict[str, object]) -> tuple[str, str]:
    return (
        str(record.get("aa_slug") or ""),
        str(record.get("aa_name") or ""),
    )


def _sorted_records(
    records: list[dict[str, object]],
    *,
    key_fn: Callable[[dict[str, object]], tuple[str, ...]],
) -> list[dict[str, object]]:
    return sorted(records, key=key_fn)


def stabilize_model_snapshot(model: ModelSnapshot) -> ModelSnapshot:
    if model.supported_parameters == sorted(model.supported_parameters):
        return model
    return model.model_copy(
        update={"supported_parameters": sorted(model.supported_parameters)},
    )


def stabilize_benchmarks(benchmarks: ModelBenchmarks) -> ModelBenchmarks:
    design_arena = benchmarks.design_arena
    stabilized_design: DesignArenaBenchmarks | None = None
    if design_arena is not None:
        stabilized_design = design_arena.model_copy(
            update={
                "records": _sorted_records(
                    design_arena.records,
                    key_fn=_design_arena_record_key,
                ),
            },
        )
    stabilized_aa = _sorted_records(
        benchmarks.artificial_analysis,
        key_fn=_aa_record_key,
    )
    if (
        design_arena is stabilized_design
        and benchmarks.artificial_analysis is stabilized_aa
    ):
        return benchmarks
    return benchmarks.model_copy(
        update={
            "design_arena": stabilized_design,
            "artificial_analysis": stabilized_aa,
        },
    )


def stabilize_enriched_model(model: EnrichedModel) -> EnrichedModel:
    stabilized_model = stabilize_model_snapshot(model.model)
    stabilized_benchmarks = stabilize_benchmarks(model.benchmarks)
    if (
        stabilized_model is model.model
        and stabilized_benchmarks is model.benchmarks
    ):
        return model
    return EnrichedModel(
        model=stabilized_model,
        benchmarks=stabilized_benchmarks,
    )


def stabilize_enriched_models(models: list[EnrichedModel]) -> list[EnrichedModel]:
    stabilized = [stabilize_enriched_model(model) for model in models]
    return sorted(stabilized, key=lambda entry: entry.model.id)
