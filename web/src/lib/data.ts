import type {
  BuildMeta,
  ModelsOutput,
  NewModelEventRecord,
  NewModelsOutput,
  PriceDropsOutput,
  PriceEventRecord,
  PriceHistoryOutput,
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
    console.warn(`Failed to load ${path}: ${response.status}; using empty events`);
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

export async function loadSiteData(): Promise<SiteData> {
  const [meta, models, priceDrops, priceEvents, newModels, newModelEvents, priceHistory] =
    await Promise.all([
      fetchJson<BuildMeta>("data/meta.json"),
      fetchJson<ModelsOutput>("data/models.json"),
      fetchJson<PriceDropsOutput>("data/price-drops.json"),
      fetchJsonlEvents<PriceEventRecord>("data/price-events.jsonl"),
      fetchJson<NewModelsOutput>("data/new-models.json"),
      fetchJsonlEvents<NewModelEventRecord>("data/new-model-events.jsonl"),
      fetchJson<PriceHistoryOutput>("data/price-history.json"),
    ]);
  return {
    meta,
    models,
    priceDrops,
    priceEvents,
    newModels,
    newModelEvents,
    priceHistory,
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
