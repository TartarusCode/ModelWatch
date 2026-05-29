from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelArchitecture(BaseModel):
    model_config = ConfigDict(frozen=True)

    input_modalities: list[str]
    output_modalities: list[str]
    modality: str | None = None
    instruct_type: str | None = None
    tokenizer: str | None = None


class TopProviderInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    context_length: int | None = None
    is_moderated: bool
    max_completion_tokens: int | None = None


class ModelPricing(BaseModel):
    model_config = ConfigDict(frozen=True)

    prompt: str
    completion: str
    image: str | None = None
    request: str | None = None
    internal_reasoning: str | None = None
    input_cache_read: str | None = None
    input_cache_write: str | None = None
    web_search: str | None = None


class ModelSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    canonical_slug: str
    name: str
    created: int
    description: str | None = None
    context_length: int | None = None
    architecture: ModelArchitecture
    pricing: ModelPricing
    top_provider: TopProviderInfo
    supported_parameters: list[str]
    default_parameters: dict[str, float | int | None] | None = None
    expiration_date: str | None = None


class BenchmarkFetchStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ok", "error", "empty"]
    error: str | None = None


class DesignArenaBenchmarks(BaseModel):
    model_config = ConfigDict(frozen=True)

    records: list[dict[str, object]]
    elo_bounds: dict[str, int] | None = None


class ArtificialAnalysisSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    intelligence_index: float
    coding_index: float
    agentic_index: float
    intelligence_percentile: int | None = None
    coding_percentile: int | None = None
    agentic_percentile: int | None = None
    variant_name: str | None = None
    aa_slug: str | None = None


class ModelBenchmarks(BaseModel):
    model_config = ConfigDict(frozen=True)

    design_arena: DesignArenaBenchmarks | None = None
    design_arena_status: BenchmarkFetchStatus
    artificial_analysis: list[dict[str, object]]
    artificial_analysis_status: BenchmarkFetchStatus
    artificial_analysis_summary: ArtificialAnalysisSummary | None = None


class EnrichedModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    model: ModelSnapshot
    benchmarks: ModelBenchmarks


class PriceDropRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    detected_at: datetime | None = None
    model_id: str
    field: str
    old_per_million_usd: str
    new_per_million_usd: str
    pct_drop: float
    saved_per_million_usd: str


class PriceDropThresholdsOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    min_pct: float
    min_saved_per_million_usd: float


class PriceDropsOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    window_hours: int = 24
    thresholds: PriceDropThresholdsOutput
    drops: list[PriceDropRecord]


class PriceEventRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    detected_at: datetime
    model_id: str
    field: str
    old_per_million_usd: str
    new_per_million_usd: str
    pct_drop: float
    saved_per_million_usd: str


class BuildMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    model_count: int
    build_duration_seconds: float
    benchmark_errors: int
    benchmark_empty: int


class ModelsOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    models: list[EnrichedModel]


class PreviousSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    models: dict[str, ModelSnapshot]
