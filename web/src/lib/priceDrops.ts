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

export function isDetectedWithinHours(
  drop: PriceDropRecord,
  hours: number,
  now: Date = new Date(),
): boolean {
  return (
    now.getTime() - new Date(drop.detected_at).getTime() <=
    hours * 60 * 60 * 1000
  );
}

export function splitDropsByFreshness(
  drops: PriceDropRecord[],
  hours: number = DROP_LOOKBACK_HOURS,
  now: Date = new Date(),
): { freshDrops: PriceDropRecord[]; olderDrops: PriceDropRecord[] } {
  const freshDrops = drops.filter((drop) =>
    isDetectedWithinHours(drop, hours, now),
  );
  const olderDrops = drops.filter(
    (drop) => !isDetectedWithinHours(drop, hours, now),
  );
  return { freshDrops, olderDrops };
}

export function dropAgeLabel(
  drop: PriceDropRecord,
  now: Date = new Date(),
): string {
  const ms = now.getTime() - new Date(drop.detected_at).getTime();
  const days = Math.floor(ms / (24 * 60 * 60 * 1000));
  if (days <= 0) {
    return "Today";
  }
  if (days === 1) {
    return "1 day ago";
  }
  return `${days} days ago`;
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
