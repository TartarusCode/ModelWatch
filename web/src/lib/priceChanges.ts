import type { PriceChangeRecord } from "../types";

export const CHANGE_LOOKBACK_HOURS = 24;

export type ChangeTimestampField =
  | "detected_at"
  | "recovered_at"
  | "settled_at";

export type ChangeDirectionFilter = "all" | "cut" | "hike";

export function sortChangesBySeverity<T extends PriceChangeRecord>(
  changes: T[],
): T[] {
  return [...changes].sort((a, b) => {
    const aMag = Math.abs(a.pct_change);
    const bMag = Math.abs(b.pct_change);
    if (bMag !== aMag) {
      return bMag - aMag;
    }
    return (
      Math.abs(Number.parseFloat(b.delta_per_million_usd)) -
      Math.abs(Number.parseFloat(a.delta_per_million_usd))
    );
  });
}

function timestampMs(
  change: PriceChangeRecord,
  field: ChangeTimestampField,
): number {
  const raw = change[field] ?? change.detected_at;
  return new Date(raw).getTime();
}

export function sortChangesChronologically<T extends PriceChangeRecord>(
  changes: T[],
  field: ChangeTimestampField = "detected_at",
): T[] {
  return [...changes].sort(
    (a, b) => timestampMs(b, field) - timestampMs(a, field),
  );
}

export function isDetectedWithinHours(
  change: PriceChangeRecord,
  hours: number,
  now: Date = new Date(),
): boolean {
  return (
    now.getTime() - new Date(change.detected_at).getTime() <=
    hours * 60 * 60 * 1000
  );
}

export function splitChangesByFreshness(
  changes: PriceChangeRecord[],
  hours: number = CHANGE_LOOKBACK_HOURS,
  now: Date = new Date(),
): { freshChanges: PriceChangeRecord[]; olderChanges: PriceChangeRecord[] } {
  const freshChanges = changes.filter((change) =>
    isDetectedWithinHours(change, hours, now),
  );
  const olderChanges = changes.filter(
    (change) => !isDetectedWithinHours(change, hours, now),
  );
  return { freshChanges, olderChanges };
}

export function changeAgeLabel(
  change: PriceChangeRecord,
  now: Date = new Date(),
): string {
  const ms = now.getTime() - new Date(change.detected_at).getTime();
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
  episodes: PriceChangeRecord[],
  modelId: string,
): PriceChangeRecord[] {
  return episodes
    .filter((episode) => episode.model_id === modelId)
    .sort(
      (left, right) =>
        new Date(right.detected_at).getTime() -
        new Date(left.detected_at).getTime(),
    );
}

export function filterChangesByDirection(
  changes: PriceChangeRecord[],
  filter: ChangeDirectionFilter,
): PriceChangeRecord[] {
  if (filter === "all") {
    return changes;
  }
  return changes.filter((change) => change.direction === filter);
}

export function countChangesByDirection(changes: PriceChangeRecord[]): {
  cuts: number;
  hikes: number;
} {
  let cuts = 0;
  let hikes = 0;
  for (const change of changes) {
    if (change.direction === "cut") {
      cuts += 1;
    } else {
      hikes += 1;
    }
  }
  return { cuts, hikes };
}
