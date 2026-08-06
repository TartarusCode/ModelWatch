import type { NewModelEventRecord, NewModelRecord } from "../types";

export const NEW_MODEL_LOOKBACK_HOURS = 24;

export const NEW_MODEL_LOOKBACK_MS = NEW_MODEL_LOOKBACK_HOURS * 60 * 60 * 1000;

export function newModelsInLast24Hours(
  events: NewModelEventRecord[],
  now: number = Date.now(),
): NewModelEventRecord[] {
  const cutoff = now - NEW_MODEL_LOOKBACK_MS;
  return events.filter(
    (event) => new Date(event.detected_at).getTime() >= cutoff,
  );
}

export function newModelRecordsLast24Hours(
  events: NewModelEventRecord[],
): NewModelRecord[] {
  return sortNewModelsByDetectedAt(
    newModelsInLast24Hours(events).map((event) => ({
      detected_at: event.detected_at,
      model_id: event.model_id,
      name: event.name,
      canonical_slug: event.canonical_slug,
      created: event.created,
    })),
  );
}

export function newModelCountLast24Hours(events: NewModelEventRecord[]): number {
  return newModelsInLast24Hours(events).length;
}

export function sortNewModelsByDetectedAt<T extends NewModelRecord>(
  models: T[],
): T[] {
  return [...models].sort((a, b) => {
    const aTime = a.detected_at ? new Date(a.detected_at).getTime() : 0;
    const bTime = b.detected_at ? new Date(b.detected_at).getTime() : 0;
    return bTime - aTime;
  });
}
