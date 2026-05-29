export interface ModelArchitecture {
  input_modalities: string[];
  output_modalities: string[];
  modality: string | null;
  instruct_type: string | null;
  tokenizer: string | null;
}

export interface TopProviderInfo {
  context_length: number | null;
  is_moderated: boolean;
  max_completion_tokens: number | null;
}

export interface ModelPricing {
  prompt: string;
  completion: string;
  image?: string;
  request?: string;
  internal_reasoning?: string;
  input_cache_read?: string;
  input_cache_write?: string;
  web_search?: string;
}

export interface ModelSnapshot {
  id: string;
  canonical_slug: string;
  name: string;
  created: number;
  description: string | null;
  context_length: number | null;
  architecture: ModelArchitecture;
  pricing: ModelPricing;
  top_provider: TopProviderInfo;
  supported_parameters: string[];
  default_parameters: Record<string, number | null> | null;
  expiration_date: string | null;
}

export interface BenchmarkFetchStatus {
  status: "ok" | "error" | "empty";
  error?: string | null;
}

export interface DesignArenaBenchmarks {
  records: Record<string, unknown>[];
  elo_bounds?: Record<string, number> | null;
}

export interface ArtificialAnalysisSummary {
  intelligence_index: number;
  coding_index: number;
  agentic_index: number;
  intelligence_percentile?: number | null;
  coding_percentile?: number | null;
  agentic_percentile?: number | null;
  variant_name?: string | null;
  aa_slug?: string | null;
}

export interface ModelBenchmarks {
  design_arena: DesignArenaBenchmarks | null;
  design_arena_status: BenchmarkFetchStatus;
  artificial_analysis: Record<string, unknown>[];
  artificial_analysis_status: BenchmarkFetchStatus;
  artificial_analysis_summary?: ArtificialAnalysisSummary | null;
}

export interface EnrichedModel {
  model: ModelSnapshot;
  benchmarks: ModelBenchmarks;
}

export interface ModelsOutput {
  generated_at: string;
  models: EnrichedModel[];
}

export interface PriceDropRecord {
  detected_at?: string | null;
  model_id: string;
  field: string;
  old_per_million_usd: string;
  new_per_million_usd: string;
  pct_drop: number;
  saved_per_million_usd: string;
}

export interface PriceDropsOutput {
  generated_at: string;
  window_hours?: number;
  thresholds: {
    min_pct: number;
    min_saved_per_million_usd: number;
  };
  drops: PriceDropRecord[];
}

export interface BuildMeta {
  generated_at: string;
  model_count: number;
  build_duration_seconds: number;
  benchmark_errors: number;
  benchmark_empty: number;
}

export interface PriceEventRecord {
  detected_at: string;
  model_id: string;
  field: string;
  old_per_million_usd: string;
  new_per_million_usd: string;
  pct_drop: number;
  saved_per_million_usd: string;
}

export interface PriceHistoryPoint {
  recorded_at: string;
  prompt_per_million?: string | null;
  completion_per_million?: string | null;
  image_per_million?: string | null;
  request_per_million?: string | null;
  internal_reasoning_per_million?: string | null;
  input_cache_read_per_million?: string | null;
  input_cache_write_per_million?: string | null;
  web_search_per_million?: string | null;
}

export interface PriceHistoryOutput {
  generated_at: string;
  models: Record<string, PriceHistoryPoint[]>;
}

export interface SiteData {
  meta: BuildMeta;
  models: ModelsOutput;
  priceDrops: PriceDropsOutput;
  priceEvents: PriceEventRecord[];
  priceHistory: PriceHistoryOutput;
}
