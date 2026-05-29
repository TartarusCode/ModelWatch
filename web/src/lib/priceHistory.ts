import type { PriceEventRecord, PriceHistoryOutput, PriceHistoryPoint } from "../types";

export interface ChartPoint {
  at: Date;
  prompt: number | null;
  completion: number | null;
}

export function getModelHistory(
  history: PriceHistoryOutput,
  modelId: string,
): PriceHistoryPoint[] {
  return history.models[modelId] ?? [];
}

export function historyToChartPoints(points: PriceHistoryPoint[]): ChartPoint[] {
  return points.map((point) => ({
    at: new Date(point.recorded_at),
    prompt: point.prompt_per_million
      ? Number.parseFloat(point.prompt_per_million)
      : null,
    completion: point.completion_per_million
      ? Number.parseFloat(point.completion_per_million)
      : null,
  }));
}

export function eventsForModel(
  events: PriceEventRecord[],
  modelId: string,
): PriceEventRecord[] {
  return events
    .filter((event) => event.model_id === modelId)
    .sort(
      (a, b) =>
        new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime(),
    );
}

export function formatHistoryUsd(value: string | null): string {
  if (value === null) {
    return "Varies";
  }
  const num = Number.parseFloat(value);
  if (Number.isNaN(num) || num === 0) {
    return "Free";
  }
  if (num < 0.01) {
    return `$${num.toFixed(4)}`;
  }
  if (num < 1) {
    return `$${num.toFixed(3)}`;
  }
  return `$${num.toFixed(2)}`;
}
