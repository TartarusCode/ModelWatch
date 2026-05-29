import type {
  BuildMeta,
  ModelsOutput,
  PriceDropsOutput,
  PriceEventRecord,
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

async function fetchPriceEvents(): Promise<PriceEventRecord[]> {
  const response = await fetch(`${base}data/price-events.jsonl`);
  if (!response.ok) {
    return [];
  }
  const text = await response.text();
  const lines = text.split("\n").filter((line) => line.trim());
  return lines.map((line) => JSON.parse(line) as PriceEventRecord);
}

export async function loadSiteData(): Promise<SiteData> {
  const [meta, models, priceDrops, priceEvents] = await Promise.all([
    fetchJson<BuildMeta>("data/meta.json"),
    fetchJson<ModelsOutput>("data/models.json"),
    fetchJson<PriceDropsOutput>("data/price-drops.json"),
    fetchPriceEvents(),
  ]);
  return { meta, models, priceDrops, priceEvents };
}

export function hasBenchmarkData(
  benchmarks: SiteData["models"]["models"][0]["benchmarks"],
): boolean {
  return (
    benchmarks.design_arena_status.status === "ok" ||
    benchmarks.artificial_analysis_status.status === "ok"
  );
}
