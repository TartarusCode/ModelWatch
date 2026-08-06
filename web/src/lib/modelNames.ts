import type { EnrichedModel } from "../types";

export function modelDisplayName(
  modelId: string,
  enriched: EnrichedModel[],
): string {
  return enriched.find((entry) => entry.model.id === modelId)?.model.name ?? modelId;
}

export function enrichedModelMap(
  enriched: EnrichedModel[],
): Map<string, EnrichedModel> {
  return new Map(enriched.map((entry) => [entry.model.id, entry]));
}
