import {
  pickAaRecord,
  shortVariantLabel,
  type AaVariantMode,
} from "./aaVariants";
import type {
  ArtificialAnalysisRecord,
  ArtificialAnalysisSummary,
  BenchmarkScoreRecord,
  DesignArenaRecord,
} from "../types";
import { isFiniteNumber } from "./pricing";

export { isFiniteNumber } from "./pricing";
export type {
  ArtificialAnalysisRecord,
  DesignArenaRecord,
} from "../types";

export function parseArtificialAnalysisRecords(
  records: ArtificialAnalysisRecord[],
): ArtificialAnalysisRecord[] {
  return records;
}

export function parseDesignArenaRecords(
  records: DesignArenaRecord[],
): DesignArenaRecord[] {
  return records;
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
  intelligence?: number;
  coding?: number;
  agentic?: number;
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
  // Artificial Analysis only publishes all three indices for some models, so a
  // summary exists as soon as one index does and the rest stay blank in the UI.
  if (!isAaIndex(intelligence) && !isAaIndex(coding) && !isAaIndex(agentic)) {
    return undefined;
  }
  return {
    ...(isAaIndex(intelligence) ? { intelligence } : {}),
    ...(isAaIndex(coding) ? { coding } : {}),
    ...(isAaIndex(agentic) ? { agentic } : {}),
    ...extras,
  };
}


export function formatAaIndex(value: number | null | undefined): string | null {
  return isFiniteNumber(value) ? value.toFixed(1) : null;
}

export function getAaSummaryScores(
  benchmarks: {
    artificial_analysis: ArtificialAnalysisRecord[];
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
      intelligencePercentile: percentiles?.intelligence_percentile ?? undefined,
      codingPercentile: percentiles?.coding_percentile ?? undefined,
      agenticPercentile: percentiles?.agentic_percentile ?? undefined,
      variantName,
      variantShort: shortVariantLabel(variantName) ?? undefined,
    },
  );
}

export function getAaVariantInfo(
  benchmarks: {
    artificial_analysis: ArtificialAnalysisRecord[];
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

const AA_INDEX_METRICS = new Set([
  "artificial_analysis_intelligence_index",
  "artificial_analysis_coding_index",
  "artificial_analysis_agentic_index",
]);

export function formatMetricValue(key: string, value: number | null | undefined): string {
  if (!isFiniteNumber(value)) {
    return "—";
  }
  // Artificial Analysis reports every non-index metric on a 0-1 scale, which
  // reads as a percentage (HLE 39.2%, SciCode 51.9%, GDPval 55.0%); the indices
  // are on a 0-100 scale and rendered as-is.
  if (AA_INDEX_METRICS.has(key) || Math.abs(value) > 1) {
    return Number.isInteger(value) ? value.toString() : value.toFixed(1);
  }
  return `${(value * 100).toFixed(1)}%`;
}

/**
 * "3h ago" for benchmark payloads, which the build refreshes daily rather than
 * on every run. Returns null when there is no usable timestamp.
 */
export function benchmarkFreshnessLabel(
  fetchedAt: string | null | undefined,
  now: Date = new Date(),
): string | null {
  if (!fetchedAt) {
    return null;
  }
  const fetched = new Date(fetchedAt);
  const ms = now.getTime() - fetched.getTime();
  if (!Number.isFinite(ms) || ms < 0) {
    return null;
  }
  const minutes = Math.floor(ms / 60_000);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }
  return `${Math.floor(hours / 24)}d ago`;
}
