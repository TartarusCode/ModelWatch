import type { PriceDropRecord, PriceEventRecord } from "../types";

export const DROP_LOOKBACK_HOURS = 24;

export const DROP_LOOKBACK_MS = DROP_LOOKBACK_HOURS * 60 * 60 * 1000;

export function dropsInLast24Hours(
  events: PriceEventRecord[],
  now: number = Date.now(),
): PriceEventRecord[] {
  const cutoff = now - DROP_LOOKBACK_MS;
  return events.filter(
    (event) => new Date(event.detected_at).getTime() >= cutoff,
  );
}

export function dropRecordsLast24Hours(
  events: PriceEventRecord[],
): PriceDropRecord[] {
  return sortDropsBySeverity(
    dropsInLast24Hours(events).map((event) => ({
      detected_at: event.detected_at,
      model_id: event.model_id,
      field: event.field,
      old_per_million_usd: event.old_per_million_usd,
      new_per_million_usd: event.new_per_million_usd,
      pct_drop: event.pct_drop,
      saved_per_million_usd: event.saved_per_million_usd,
    })),
  );
}

export function dropCountLast24Hours(events: PriceEventRecord[]): number {
  return dropsInLast24Hours(events).length;
}

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
