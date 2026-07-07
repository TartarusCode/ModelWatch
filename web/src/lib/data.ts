import type {
  BuildMeta,
  ModelHistorySeries,
  ModelsOutput,
  NewModelEventRecord,
  NewModelsOutput,
  PriceDropsOutput,
  PriceHistoryPoint,
  SiteData,
} from "../types";

const base = import.meta.env.BASE_URL;

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${base}${path}`);
  if (!response.ok) {
    throw new Error(`Failed to load ${path}: ${response.status}`);
  }
  return (await response.json()) as T;
}

async function fetchJsonlEvents<T>(path: string): Promise<T[]> {
  const response = await fetch(`${base}${path}`);
  if (!response.ok) {
    return [];
  }
  const text = await response.text();
  const lines = text.split("\n").filter((line) => line.trim());
  const events: T[] = [];
  for (const [index, line] of lines.entries()) {
    try {
      events.push(JSON.parse(line) as T);
    } catch (error) {
      console.warn(`Skipping malformed JSONL line ${index + 1} in ${path}`, error);
    }
  }
  return events;
}

export function encodeModelIdForHistory(modelId: string): string {
  return modelId.replace(/\//g, "__").replace(/:/g, "_colon_");
}

export async function fetchModelPriceHistory(
  modelId: string,
): Promise<PriceHistoryPoint[]> {
  const encoded = encodeModelIdForHistory(modelId);
  const response = await fetch(
    `${base}data/price-history/models/${encoded}.json`,
  );
  if (response.status === 404) {
    return [];
  }
  if (!response.ok) {
    throw new Error(`Failed to load price history for ${modelId}: ${response.status}`);
  }
  const series = (await response.json()) as ModelHistorySeries;
  return series.points;
}

export async function loadSiteData(): Promise<SiteData> {
  const [meta, models, priceDrops, newModels, newModelEvents] = await Promise.all([
    fetchJson<BuildMeta>("data/meta.json"),
    fetchJson<ModelsOutput>("data/models.json"),
    fetchJson<PriceDropsOutput>("data/price-drops.json"),
    fetchJson<NewModelsOutput>("data/new-models.json"),
    fetchJsonlEvents<NewModelEventRecord>("data/new-model-events.jsonl"),
  ]);
  return {
    meta,
    models,
    priceDrops,
    newModels,
    newModelEvents,
  };
}

export function hasBenchmarkData(
  benchmarks: SiteData["models"]["models"][0]["benchmarks"],
): boolean {
  return (
    benchmarks.design_arena_status.status === "ok" ||
    benchmarks.artificial_analysis_status.status === "ok"
  );
}
