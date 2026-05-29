import type { PriceEventRecord, PriceHistoryOutput, PriceHistoryPoint } from "../types";
import { pricingFieldLabel } from "./pricing";

export const PRICE_HISTORY_FIELDS = [
  "prompt",
  "completion",
  "image",
  "request",
  "internal_reasoning",
  "input_cache_read",
  "input_cache_write",
  "web_search",
] as const;

export type PriceHistoryField = (typeof PRICE_HISTORY_FIELDS)[number];

export const CHART_SERIES_COLORS: Record<PriceHistoryField, string> = {
  prompt: "#a78bfa",
  completion: "#4ade80",
  image: "#fbbf24",
  request: "#38bdf8",
  internal_reasoning: "#f472b6",
  input_cache_read: "#fb923c",
  input_cache_write: "#a3e635",
  web_search: "#94a3b8",
};

export interface ChartPoint {
  at: Date;
  values: Record<PriceHistoryField, number | null>;
}

export function historyPerMillionKey(field: PriceHistoryField): keyof PriceHistoryPoint {
  return `${field}_per_million` as keyof PriceHistoryPoint;
}

export function getModelHistory(
  history: PriceHistoryOutput,
  modelId: string,
): PriceHistoryPoint[] {
  return history.models[modelId] ?? [];
}

export function parseHistoryPerMillion(
  point: PriceHistoryPoint,
  field: PriceHistoryField,
): number | null {
  const raw = point[historyPerMillionKey(field)];
  if (raw === null || raw === undefined) {
    return null;
  }
  const num = Number.parseFloat(raw);
  return Number.isFinite(num) ? num : null;
}

export function historyToChartPoints(points: PriceHistoryPoint[]): ChartPoint[] {
  return points.map((point) => ({
    at: new Date(point.recorded_at),
    values: Object.fromEntries(
      PRICE_HISTORY_FIELDS.map((field) => [
        field,
        parseHistoryPerMillion(point, field),
      ]),
    ) as Record<PriceHistoryField, number | null>,
  }));
}

export function activeHistoryFields(
  points: PriceHistoryPoint[],
): PriceHistoryField[] {
  return PRICE_HISTORY_FIELDS.filter((field) =>
    points.some((point) => parseHistoryPerMillion(point, field) !== null),
  );
}

export function historyColumnLabel(field: PriceHistoryField): string {
  return pricingFieldLabel(field);
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

export function formatHistoryUsd(value: string | null | undefined): string {
  if (value === null || value === undefined) {
    return "—";
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
