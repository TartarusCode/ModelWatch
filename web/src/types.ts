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

export interface ArtificialAnalysisEvaluations {
  artificial_analysis_intelligence_index?: number;
  artificial_analysis_coding_index?: number;
  artificial_analysis_agentic_index?: number;
  gdpval_aa?: number;
  aa_omniscience_accuracy?: number;
  aa_omniscience_non_hallucination_rate?: number;
  lcr?: number;
  ifbench?: number;
  gpqa?: number;
  hle?: number;
  scicode?: number;
  terminalbench_hard?: number;
  critpt?: number;
  tau2?: number;
}

export interface ArtificialAnalysisRecord {
  aa_id?: string;
  aa_slug?: string;
  aa_name?: string;
  permaslug?: string;
  openrouter_slug?: string | null;
  heuristic_openrouter_slug?: string | null;
  benchmark_data?: {
    model_type?: string;
    evaluations?: ArtificialAnalysisEvaluations;
  };
  last_updated_at?: number;
  percentiles?: {
    intelligence_percentile?: number;
    coding_percentile?: number;
    agentic_percentile?: number;
  };
}

export interface DesignArenaRecord {
  da_model_id?: string;
  display_name?: string;
  provider?: string;
  openrouter_id?: string;
  permaslug?: string;
  arena?: string;
  category?: string;
  elo?: number;
  win_rate?: number;
  avg_generation_time_ms?: number;
  last_updated_at?: number;
  elo_percentile?: number;
  total_tournaments?: number;
}

export interface EloBounds {
  min: number;
  max: number;
}

export interface DesignArenaBenchmarks {
  records: DesignArenaRecord[];
  elo_bounds?: EloBounds | null;
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

export interface BenchmarkScoreRecord {
  provider_name: string;
  benchmark_type: string;
  score: number;
  run_count: number;
}

export interface EffectivePricingProviderSummary {
  provider_name: string;
  provider_slug: string;
  effective_input_price: number;
  effective_output_price: number;
  cache_hit_rate: number;
  total_tokens: number;
}

export interface EffectivePricing {
  weighted_input_price?: number | null;
  weighted_output_price?: number | null;
  weighted_cache_hit_rate?: number | null;
  provider_summaries: EffectivePricingProviderSummary[];
}

export interface ProviderEndpointPricing {
  prompt: string;
  completion: string;
}

export interface ProviderEndpoint {
  provider_name: string;
  name: string;
  pricing: ProviderEndpointPricing;
  uptime_last_30m?: number | null;
  context_length?: number | null;
}

export interface ModelProviderStats {
  effective_pricing: EffectivePricing | null;
  effective_pricing_status: BenchmarkFetchStatus;
  provider_endpoints: ProviderEndpoint[];
  provider_endpoints_status: BenchmarkFetchStatus;
}

export interface ModelBenchmarks {
  design_arena: DesignArenaBenchmarks | null;
  design_arena_status: BenchmarkFetchStatus;
  artificial_analysis: ArtificialAnalysisRecord[];
  artificial_analysis_status: BenchmarkFetchStatus;
  artificial_analysis_summary?: ArtificialAnalysisSummary | null;
  benchmark_scores?: BenchmarkScoreRecord[] | null;
  benchmark_scores_status: BenchmarkFetchStatus;
}

export interface EnrichedModel {
  model: ModelSnapshot;
  benchmarks: ModelBenchmarks;
  provider_stats: ModelProviderStats;
}

export interface ModelsOutput {
  generated_at: string;
  models: EnrichedModel[];
}

export interface PriceDropRecord {
  detected_at: string;
  model_id: string;
  field: string;
  episode_start_per_million_usd: string;
  old_per_million_usd: string;
  new_per_million_usd: string;
  pct_drop: number;
  saved_per_million_usd: string;
  status: "active" | "recovered";
  recovered_at?: string | null;
  recovered_per_million_usd?: string | null;
}

export interface PriceDropsOutput {
  generated_at: string;
  window_hours?: number;
  thresholds: {
    min_pct: number;
    min_saved_per_million_usd: number;
  };
  active_drops: PriceDropRecord[];
  recovered_drops: PriceDropRecord[];
  episodes: PriceDropRecord[];
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
  episode_start_per_million_usd: string;
  old_per_million_usd: string;
  new_per_million_usd: string;
  pct_drop: number;
  saved_per_million_usd: string;
  status: "active" | "recovered";
  recovered_at?: string | null;
  recovered_per_million_usd?: string | null;
}

export interface NewModelRecord {
  detected_at?: string | null;
  model_id: string;
  name: string;
  canonical_slug: string;
  created: number;
}

export interface NewModelsOutput {
  generated_at: string;
  window_hours?: number;
  models: NewModelRecord[];
}

export interface NewModelEventRecord {
  detected_at: string;
  model_id: string;
  name: string;
  canonical_slug: string;
  created: number;
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
  newModels: NewModelsOutput;
  newModelEvents: NewModelEventRecord[];
  priceHistory: PriceHistoryOutput;
}
