from typing import Literal

from modelwatch.schemas import ArtificialAnalysisSummary

AaVariantMode = Literal[
    "auto",
    "max-effort",
    "high-effort",
    "non-reasoning",
    "medium",
]


def _base_model_slug(model_id: str) -> str:
    return model_id.split(":", 1)[0]


def _slug_matches_model(record: dict[str, object], model_id: str) -> bool:
    base = _base_model_slug(model_id)
    for key in ("openrouter_slug", "heuristic_openrouter_slug"):
        value = record.get(key)
        if isinstance(value, str) and value == base:
            return True
    return False


def _intelligence_index(record: dict[str, object]) -> float | None:
    benchmark_data = record.get("benchmark_data")
    if not isinstance(benchmark_data, dict):
        return None
    evaluations = benchmark_data.get("evaluations")
    if not isinstance(evaluations, dict):
        return None
    value = evaluations.get("artificial_analysis_intelligence_index")
    return float(value) if isinstance(value, (int, float)) else None


def classify_aa_variant(record: dict[str, object]) -> str:
    name = str(record.get("aa_name") or "").lower()
    slug = str(record.get("aa_slug") or "").lower()
    if "non-reasoning" in name or "non-reasoning" in slug:
        return "non-reasoning"
    if "high effort" in name or slug.endswith("-high"):
        return "high-effort"
    if "max effort" in name or "xhigh" in name:
        return "max-effort"
    if "medium" in name or slug.endswith("-medium"):
        return "medium"
    aa_slug = record.get("aa_slug")
    if isinstance(aa_slug, str) and aa_slug:
        return aa_slug
    return "other"


def pick_primary_aa_record(
    records: list[dict[str, object]],
    *,
    model_id: str,
) -> dict[str, object] | None:
    return pick_aa_record(records, model_id=model_id, variant="auto")


def pick_aa_record(
    records: list[dict[str, object]],
    *,
    model_id: str,
    variant: AaVariantMode | str = "auto",
) -> dict[str, object] | None:
    if not records:
        return None

    if variant == "auto":
        linked = [record for record in records if _slug_matches_model(record, model_id)]
        if linked:
            return max(
                linked,
                key=lambda record: _intelligence_index(record) or -1.0,
            )

        max_effort = [
            record for record in records if classify_aa_variant(record) == "max-effort"
        ]
        if max_effort:
            return max(
                max_effort,
                key=lambda record: _intelligence_index(record) or -1.0,
            )

        return max(records, key=lambda record: _intelligence_index(record) or -1.0)

    matched = [
        record
        for record in records
        if classify_aa_variant(record) == variant or record.get("aa_slug") == variant
    ]
    if matched:
        return max(matched, key=lambda record: _intelligence_index(record) or -1.0)

    return pick_aa_record(records, model_id=model_id, variant="auto")


def _optional_float(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _optional_int(value: object) -> int | None:
    return int(value) if isinstance(value, (int, float)) else None


def extract_aa_summary(record: dict[str, object]) -> ArtificialAnalysisSummary | None:
    benchmark_data = record.get("benchmark_data")
    if not isinstance(benchmark_data, dict):
        return None
    evaluations = benchmark_data.get("evaluations")
    if not isinstance(evaluations, dict):
        return None

    intelligence = _optional_float(
        evaluations.get("artificial_analysis_intelligence_index")
    )
    coding = _optional_float(evaluations.get("artificial_analysis_coding_index"))
    agentic = _optional_float(evaluations.get("artificial_analysis_agentic_index"))
    if intelligence is None or coding is None or agentic is None:
        return None

    percentiles = record.get("percentiles")
    percentile_map = percentiles if isinstance(percentiles, dict) else {}

    aa_slug = record.get("aa_slug")
    aa_name = record.get("aa_name")

    return ArtificialAnalysisSummary(
        intelligence_index=intelligence,
        coding_index=coding,
        agentic_index=agentic,
        intelligence_percentile=_optional_int(
            percentile_map.get("intelligence_percentile")
        ),
        coding_percentile=_optional_int(percentile_map.get("coding_percentile")),
        agentic_percentile=_optional_int(percentile_map.get("agentic_percentile")),
        variant_name=str(aa_name) if isinstance(aa_name, str) else None,
        aa_slug=str(aa_slug) if isinstance(aa_slug, str) else None,
    )


def summarize_artificial_analysis(
    records: list[dict[str, object]],
    *,
    model_id: str,
    variant: AaVariantMode | str = "auto",
) -> ArtificialAnalysisSummary | None:
    primary = pick_aa_record(records, model_id=model_id, variant=variant)
    if primary is None:
        return None
    return extract_aa_summary(primary)
