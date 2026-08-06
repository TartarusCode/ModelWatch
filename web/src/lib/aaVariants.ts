import type { ArtificialAnalysisRecord } from "./benchmarks";

export type AaVariantMode =
  | "auto"
  | "max-effort"
  | "high-effort"
  | "non-reasoning"
  | "medium";

export interface AaVariantOption {
  value: AaVariantMode;
  label: string;
  description: string;
}

export const AA_VARIANT_OPTIONS: AaVariantOption[] = [
  {
    value: "auto",
    label: "Auto",
    description: "Match OpenRouter slug when possible, else max effort",
  },
  {
    value: "max-effort",
    label: "Max effort",
    description: "Reasoning, max / xhigh effort benchmark profile",
  },
  {
    value: "high-effort",
    label: "High effort",
    description: "Reasoning, high effort benchmark profile",
  },
  {
    value: "non-reasoning",
    label: "Non-reasoning",
    description: "Benchmark profile without reasoning",
  },
  {
    value: "medium",
    label: "Medium",
    description: "Medium effort profile (e.g. GPT mini medium)",
  },
];

export type ModelAaVariantSelection = "default" | string;

function modelVariantStorageKey(modelId: string): string {
  return `modelwatch.model.${modelId}.aaVariant`;
}

export function loadModelAaVariant(modelId: string): ModelAaVariantSelection {
  try {
    const raw = localStorage.getItem(modelVariantStorageKey(modelId));
    return raw && raw.length > 0 ? raw : "default";
  } catch {
    return "default";
  }
}

export function saveModelAaVariant(
  modelId: string,
  selection: ModelAaVariantSelection,
): void {
  try {
    localStorage.setItem(modelVariantStorageKey(modelId), selection);
  } catch {
    // ignore
  }
}

export function resolveAaRecord(
  records: ArtificialAnalysisRecord[],
  modelId: string,
  selection: ModelAaVariantSelection,
): ArtificialAnalysisRecord | undefined {
  if (selection === "default") {
    return pickAaRecord(records, modelId, "auto");
  }
  const matched = records.find(
    (record) => record.aa_slug === selection || record.aa_id === selection,
  );
  return matched ?? pickAaRecord(records, modelId, "auto");
}

function baseModelSlug(modelId: string): string {
  return modelId.split(":", 1)[0] ?? modelId;
}

function slugMatchesModel(
  record: ArtificialAnalysisRecord,
  modelId: string,
): boolean {
  const base = baseModelSlug(modelId);
  return (
    record.openrouter_slug === base ||
    record.heuristic_openrouter_slug === base
  );
}

function intelligenceIndex(record: ArtificialAnalysisRecord): number {
  return (
    record.benchmark_data?.evaluations
      ?.artificial_analysis_intelligence_index ?? -1
  );
}

export function classifyAaVariant(record: ArtificialAnalysisRecord): string {
  const name = record.aa_name?.toLowerCase() ?? "";
  const slug = record.aa_slug?.toLowerCase() ?? "";
  if (name.includes("non-reasoning") || slug.includes("non-reasoning")) {
    return "non-reasoning";
  }
  if (name.includes("high effort") || slug.endsWith("-high")) {
    return "high-effort";
  }
  if (name.includes("max effort") || name.includes("xhigh")) {
    return "max-effort";
  }
  if (name.includes("medium") || slug.endsWith("-medium")) {
    return "medium";
  }
  return record.aa_slug ?? "other";
}

export function pickAaRecord(
  records: ArtificialAnalysisRecord[],
  modelId: string,
  variant: AaVariantMode | string,
): ArtificialAnalysisRecord | undefined {
  if (records.length === 0) {
    return undefined;
  }

  if (variant === "auto") {
    const linked = records.filter((record) => slugMatchesModel(record, modelId));
    if (linked.length > 0) {
      return linked.reduce((best, record) =>
        intelligenceIndex(record) > intelligenceIndex(best) ? record : best,
      );
    }
    const maxEffort = records.filter(
      (record) => classifyAaVariant(record) === "max-effort",
    );
    if (maxEffort.length > 0) {
      return maxEffort.reduce((best, record) =>
        intelligenceIndex(record) > intelligenceIndex(best) ? record : best,
      );
    }
    return records.reduce((best, record) =>
      intelligenceIndex(record) > intelligenceIndex(best) ? record : best,
    );
  }

  const matched = records.filter(
    (record) =>
      classifyAaVariant(record) === variant || record.aa_slug === variant,
  );
  if (matched.length > 0) {
    return matched.reduce((best, record) =>
      intelligenceIndex(record) > intelligenceIndex(best) ? record : best,
    );
  }

  return pickAaRecord(records, modelId, "auto");
}

export function shortVariantLabel(variantName: string | undefined): string | null {
  if (!variantName) {
    return null;
  }
  const match = variantName.match(/\(([^)]+)\)/);
  if (match?.[1]) {
    return match[1];
  }
  return variantName;
}
