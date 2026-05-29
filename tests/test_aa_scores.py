from modelwatch.aa_scores import (
    classify_aa_variant,
    extract_aa_summary,
    pick_aa_record,
    pick_primary_aa_record,
)


def _aa_record(
    *,
    aa_slug: str,
    aa_name: str,
    intelligence: float,
    coding: float,
    agentic: float,
    heuristic_openrouter_slug: str | None = None,
    openrouter_slug: str | None = None,
) -> dict[str, object]:
    return {
        "aa_slug": aa_slug,
        "aa_name": aa_name,
        "heuristic_openrouter_slug": heuristic_openrouter_slug,
        "openrouter_slug": openrouter_slug,
        "benchmark_data": {
            "model_type": "llm",
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


def test_pick_primary_prefers_heuristic_openrouter_slug_match() -> None:
    records = [
        _aa_record(
            aa_slug="model-non-reasoning",
            aa_name="Model (Non-reasoning)",
            intelligence=36.5,
            coding=35.2,
            agentic=61.3,
        ),
        _aa_record(
            aa_slug="model",
            aa_name="Model (Reasoning, Max Effort)",
            intelligence=46.5,
            coding=38.7,
            agentic=61.3,
            heuristic_openrouter_slug="vendor/model",
        ),
    ]

    picked = pick_primary_aa_record(records, model_id="vendor/model:free")

    assert picked is not None
    assert picked["aa_slug"] == "model"


def test_pick_primary_falls_back_to_highest_intelligence() -> None:
    records = [
        _aa_record(
            aa_slug="low",
            aa_name="Low",
            intelligence=30.0,
            coding=30.0,
            agentic=50.0,
        ),
        _aa_record(
            aa_slug="high",
            aa_name="High",
            intelligence=45.0,
            coding=40.0,
            agentic=60.0,
        ),
    ]

    picked = pick_primary_aa_record(records, model_id="vendor/other")

    assert picked is not None
    assert picked["aa_slug"] == "high"


def test_extract_aa_summary_returns_indices_and_percentiles() -> None:
    record = _aa_record(
        aa_slug="model",
        aa_name="Model (Max Effort)",
        intelligence=46.5,
        coding=38.7,
        agentic=61.3,
        heuristic_openrouter_slug="vendor/model",
    )

    summary = extract_aa_summary(record)

    assert summary is not None
    assert summary.intelligence_index == 46.5
    assert summary.coding_index == 38.7
    assert summary.agentic_index == 61.3
    assert summary.intelligence_percentile == 80
    assert summary.variant_name == "Model (Max Effort)"
    assert summary.aa_slug == "model"


def test_pick_aa_record_by_non_reasoning_variant() -> None:
    records = [
        _aa_record(
            aa_slug="deepseek-v4-flash",
            aa_name="DeepSeek V4 Flash (Reasoning, Max Effort)",
            intelligence=46.5,
            coding=38.7,
            agentic=61.3,
        ),
        _aa_record(
            aa_slug="deepseek-v4-flash-non-reasoning",
            aa_name="DeepSeek V4 Flash (Non-reasoning)",
            intelligence=36.5,
            coding=35.2,
            agentic=61.3,
        ),
    ]

    picked = pick_aa_record(
        records,
        model_id="deepseek/deepseek-v4-flash",
        variant="non-reasoning",
    )

    assert picked is not None
    assert picked["aa_slug"] == "deepseek-v4-flash-non-reasoning"


def test_classify_aa_variant_buckets() -> None:
    assert (
        classify_aa_variant(
            _aa_record(
                aa_slug="m",
                aa_name="M (Reasoning, Max Effort)",
                intelligence=1,
                coding=1,
                agentic=1,
            )
        )
        == "max-effort"
    )
    assert (
        classify_aa_variant(
            _aa_record(
                aa_slug="m-high",
                aa_name="M (Reasoning, High Effort)",
                intelligence=1,
                coding=1,
                agentic=1,
            )
        )
        == "high-effort"
    )


def test_extract_aa_summary_returns_none_when_indices_missing() -> None:
    record: dict[str, object] = {
        "aa_slug": "empty",
        "benchmark_data": {"evaluations": {}},
    }

    assert extract_aa_summary(record) is None
