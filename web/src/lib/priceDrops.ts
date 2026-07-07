import type { PriceDropRecord } from "../types";

export const DROP_LOOKBACK_HOURS = 24;

export function sortDropsBySeverity<T extends PriceDropRecord>(
  drops: T[],
): T[] {
  return [...drops].sort((a, b) => {
    if (b.pct_drop !== a.pct_drop) {
      return b.pct_drop - a.pct_drop;
    }
    return (
      Number.parseFloat(b.saved_per_million_usd) -
      Number.parseFloat(a.saved_per_million_usd)
    );
  });
}

export function episodesForModel(
  episodes: PriceDropRecord[],
  modelId: string,
): PriceDropRecord[] {
  return episodes
    .filter((episode) => episode.model_id === modelId)
    .sort(
      (left, right) =>
        new Date(right.detected_at).getTime() -
        new Date(left.detected_at).getTime(),
    );
}
