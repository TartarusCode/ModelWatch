import type {
  BenchmarkFetchStatus,
  EffectivePricing,
  ModelProviderStats,
  ProviderEndpoint,
} from "../types";
import { formatPerMillionUsd, isFiniteNumber } from "./pricing";

export interface MergedProviderRow {
  providerName: string;
  listPrompt: string | null;
  listCompletion: string | null;
  effectiveInputPrice: number | null;
  effectiveOutputPrice: number | null;
  cacheHitRate: number | null;
  uptimeLast30m: number | null;
}

export function normalizeProviderKey(value: string): string {
  return value.trim().toLowerCase().replace(/[^a-z0-9]/g, "");
}

export function mergeProviderRows(
  effectivePricing: EffectivePricing | null,
  endpoints: ProviderEndpoint[],
): MergedProviderRow[] {
  const rowsByKey = new Map<string, MergedProviderRow>();

  for (const summary of effectivePricing?.provider_summaries ?? []) {
    const key = normalizeProviderKey(summary.provider_slug);
    rowsByKey.set(key, {
      providerName: summary.provider_name,
      listPrompt: null,
      listCompletion: null,
      effectiveInputPrice: summary.effective_input_price,
      effectiveOutputPrice: summary.effective_output_price,
      cacheHitRate: summary.cache_hit_rate,
      uptimeLast30m: null,
    });
  }

  for (const endpoint of endpoints) {
    const key = normalizeProviderKey(endpoint.provider_name);
    const existing = rowsByKey.get(key);
    if (!existing) {
      rowsByKey.set(key, {
        providerName: endpoint.provider_name,
        listPrompt: endpoint.pricing.prompt,
        listCompletion: endpoint.pricing.completion,
        effectiveInputPrice: null,
        effectiveOutputPrice: null,
        cacheHitRate: null,
        uptimeLast30m: endpoint.uptime_last_30m ?? null,
      });
      continue;
    }
    rowsByKey.set(key, {
      ...existing,
      listPrompt: endpoint.pricing.prompt,
      listCompletion: endpoint.pricing.completion,
      uptimeLast30m: endpoint.uptime_last_30m ?? null,
    });
  }

  return [...rowsByKey.values()].sort((left, right) =>
    left.providerName.localeCompare(right.providerName),
  );
}

export function hasProviderPricingData(stats: ModelProviderStats): boolean {
  return (
    stats.effective_pricing_status.status === "ok" ||
    stats.provider_endpoints_status.status === "ok"
  );
}

export function formatCacheHitRate(value: number | null | undefined): string {
  if (!isFiniteNumber(value)) {
    return "—";
  }
  return `${(value * 100).toFixed(1)}%`;
}

export function formatUptime(value: number | null | undefined): string {
  if (!isFiniteNumber(value)) {
    return "—";
  }
  return `${(value * 100).toFixed(1)}%`;
}

export function effectivePricingSubtitle(
  effectivePricing: EffectivePricing | null,
): string | null {
  if (!effectivePricing) {
    return null;
  }
  const parts: string[] = [];
  if (effectivePricing.weighted_input_price != null) {
    parts.push(
      `Weighted input ${formatPerMillionUsd(String(effectivePricing.weighted_input_price))}`,
    );
  }
  if (effectivePricing.weighted_output_price != null) {
    parts.push(
      `output ${formatPerMillionUsd(String(effectivePricing.weighted_output_price))}`,
    );
  }
  if (effectivePricing.weighted_cache_hit_rate != null) {
    parts.push(
      `cache hit ${formatCacheHitRate(effectivePricing.weighted_cache_hit_rate)}`,
    );
  }
  return parts.length > 0 ? parts.join("; ") : null;
}

export function providerStatsErrors(stats: ModelProviderStats): string[] {
  const errors: string[] = [];
  for (const [label, status] of [
    ["Effective pricing", stats.effective_pricing_status],
    ["List endpoints", stats.provider_endpoints_status],
  ] as const) {
    if (status.status === "error" && status.error) {
      errors.push(`${label}: ${status.error}`);
    }
  }
  return errors;
}

export function isFetchStatusEmpty(status: BenchmarkFetchStatus): boolean {
  return status.status === "empty";
}
