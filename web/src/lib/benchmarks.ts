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

export function parseArtificialAnalysisRecords(
  records: Record<string, unknown>[],
): ArtificialAnalysisRecord[] {
  return records.map((record) => record as ArtificialAnalysisRecord);
}

export function parseDesignArenaRecords(
  records: Record<string, unknown>[],
): DesignArenaRecord[] {
  return records.map((record) => record as DesignArenaRecord);
}

export function formatAaMetricLabel(key: string): string {
  const labels: Record<string, string> = {
    artificial_analysis_intelligence_index: "Intelligence index",
    artificial_analysis_coding_index: "Coding index",
    artificial_analysis_agentic_index: "Agentic index",
    gdpval_aa: "GDPval",
    aa_omniscience_accuracy: "Omniscience accuracy",
    aa_omniscience_non_hallucination_rate: "Non-hallucination rate",
    lcr: "LCR",
    ifbench: "IFBench",
    gpqa: "GPQA",
    hle: "HLE",
    scicode: "SciCode",
    terminalbench_hard: "TerminalBench Hard",
    critpt: "CritPt",
    tau2: "Tau2",
  };
  return labels[key] ?? key.replaceAll("_", " ");
}

export function formatMetricValue(key: string, value: number): string {
  if (key.includes("rate") || key === "gdpval_aa") {
    return `${(value * 100).toFixed(1)}%`;
  }
  if (Number.isInteger(value)) {
    return value.toString();
  }
  return value.toFixed(1);
}
