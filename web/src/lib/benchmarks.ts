import {
  pickAaRecord,
  shortVariantLabel,
  type AaVariantMode,
} from "./aaVariants";
import type { ArtificialAnalysisSummary, BenchmarkScoreRecord } from "../types";
import { isFiniteNumber } from "./pricing";

export { isFiniteNumber } from "./pricing";

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

export interface AaSummaryScores {
  intelligence: number;
  coding: number;
  agentic: number;
  intelligencePercentile?: number;
  codingPercentile?: number;
  agenticPercentile?: number;
  variantName?: string;
  variantShort?: string;
}

export interface AaVariantInfo {
  defaultLabel: string | null;
  defaultName: string | null;
  totalVariants: number;
  additionalCount: number;
  otherVariantNames: string[];
}

function isAaIndex(value: unknown): value is number {
  return isFiniteNumber(value);
}

function buildAaSummaryScores(
  intelligence: unknown,
  coding: unknown,
  agentic: unknown,
  extras: Omit<AaSummaryScores, "intelligence" | "coding" | "agentic">,
): AaSummaryScores | undefined {
  if (!isAaIndex(intelligence) || !isAaIndex(coding) || !isAaIndex(agentic)) {
    return undefined;
  }
  return {
    intelligence,
    coding,
    agentic,
    ...extras,
  };
}


export function formatAaIndex(value: number | null | undefined): string | null {
  return isFiniteNumber(value) ? value.toFixed(1) : null;
}

export function getAaSummaryScores(
  benchmarks: {
    artificial_analysis: Record<string, unknown>[];
    artificial_analysis_summary?: ArtificialAnalysisSummary | null;
  },
  modelId: string,
  variant: AaVariantMode | string = "auto",
): AaSummaryScores | undefined {
  if (variant === "auto") {
    const summary = benchmarks.artificial_analysis_summary;
    if (summary) {
      return buildAaSummaryScores(
        summary.intelligence_index,
        summary.coding_index,
        summary.agentic_index,
        {
          intelligencePercentile: summary.intelligence_percentile ?? undefined,
          codingPercentile: summary.coding_percentile ?? undefined,
          agenticPercentile: summary.agentic_percentile ?? undefined,
          variantName: summary.variant_name ?? undefined,
          variantShort:
            shortVariantLabel(summary.variant_name ?? undefined) ?? undefined,
        },
      );
    }
  }

  const records = parseArtificialAnalysisRecords(
    benchmarks.artificial_analysis,
  );
  const primary = pickAaRecord(records, modelId, variant);
  const evaluations = primary?.benchmark_data?.evaluations;
  const percentiles = primary?.percentiles;
  const variantName = primary?.aa_name ?? undefined;
  return buildAaSummaryScores(
    evaluations?.artificial_analysis_intelligence_index,
    evaluations?.artificial_analysis_coding_index,
    evaluations?.artificial_analysis_agentic_index,
    {
      intelligencePercentile: percentiles?.intelligence_percentile,
      codingPercentile: percentiles?.coding_percentile,
      agenticPercentile: percentiles?.agentic_percentile,
      variantName,
      variantShort: shortVariantLabel(variantName) ?? undefined,
    },
  );
}

export function getAaVariantInfo(
  benchmarks: {
    artificial_analysis: Record<string, unknown>[];
    artificial_analysis_summary?: ArtificialAnalysisSummary | null;
  },
  modelId: string,
): AaVariantInfo | undefined {
  const records = parseArtificialAnalysisRecords(
    benchmarks.artificial_analysis,
  );
  if (records.length === 0) {
    return undefined;
  }

  const defaultScores = getAaSummaryScores(benchmarks, modelId);
  const defaultName = defaultScores?.variantName ?? null;
  const defaultLabel = defaultScores?.variantShort ?? null;

  const allNames = records
    .map((record) => record.aa_name ?? record.aa_slug)
    .filter((name): name is string => typeof name === "string" && name.length > 0);

  const otherVariantNames = allNames.filter((name) => name !== defaultName);

  return {
    defaultLabel,
    defaultName,
    totalVariants: records.length,
    additionalCount: Math.max(0, records.length - 1),
    otherVariantNames,
  };
}

export interface BenchmarkScorePivotRow {
  providerName: string;
  scores: Record<string, { score: number; runCount: number }>;
}

const BENCHMARK_TYPE_LABELS: Record<string, string> = {
  gpqa_diamond: "GPQA Diamond",
  tau_bench_verified_airline: "Tau Bench Airline",
};

export function formatBenchmarkType(type: string): string {
  return BENCHMARK_TYPE_LABELS[type] ?? type.replaceAll("_", " ");
}

export function pivotBenchmarkScores(
  records: BenchmarkScoreRecord[],
): { types: string[]; rows: BenchmarkScorePivotRow[] } {
  const types = [...new Set(records.map((record) => record.benchmark_type))].sort();
  const rowsByProvider = new Map<string, BenchmarkScorePivotRow>();

  for (const record of records) {
    const existing = rowsByProvider.get(record.provider_name) ?? {
      providerName: record.provider_name,
      scores: {},
    };
    existing.scores[record.benchmark_type] = {
      score: record.score,
      runCount: record.run_count,
    };
    rowsByProvider.set(record.provider_name, existing);
  }

  const rows = [...rowsByProvider.values()].sort((left, right) =>
    left.providerName.localeCompare(right.providerName),
  );
  return { types, rows };
}

export function formatBenchmarkScore(score: number | null | undefined): string {
  if (!isFiniteNumber(score)) {
    return "—";
  }
  return `${(score * 100).toFixed(1)}%`;
}

export function formatMetricValue(key: string, value: number | null | undefined): string {
  if (!isFiniteNumber(value)) {
    return "—";
  }
  if (key.includes("rate") || key === "gdpval_aa") {
    return `${(value * 100).toFixed(1)}%`;
  }
  if (Number.isInteger(value)) {
    return value.toString();
  }
  return value.toFixed(1);
}
