export type ParsedTokenPrice =
  | { kind: "free" }
  | { kind: "variable" }
  | { kind: "priced"; perMillion: number };

export function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function parseTokenPrice(perToken: string): ParsedTokenPrice {
  const value = Number.parseFloat(perToken);
  if (Number.isNaN(value) || value < 0) {
    return { kind: "variable" };
  }
  if (value === 0) {
    return { kind: "free" };
  }
  return { kind: "priced", perMillion: value * 1_000_000 };
}

export function perMillionFromTokenString(perToken: string): number | null {
  const parsed = parseTokenPrice(perToken);
  if (parsed.kind === "priced") {
    return parsed.perMillion;
  }
  return null;
}

function formatPerMillionValue(perMillion: number): string {
  if (perMillion < 0.01) {
    return `$${perMillion.toFixed(4)}/M`;
  }
  if (perMillion < 1) {
    return `$${perMillion.toFixed(3)}/M`;
  }
  return `$${perMillion.toFixed(2)}/M`;
}

export function formatPerMillion(perToken: string): string {
  const parsed = parseTokenPrice(perToken);
  if (parsed.kind === "free") {
    return "Free";
  }
  if (parsed.kind === "variable") {
    return "Varies";
  }
  return formatPerMillionValue(parsed.perMillion);
}

export function formatPerMillionUsd(
  value: string | number | null | undefined,
): string {
  const num =
    typeof value === "number" ? value : Number.parseFloat(String(value ?? ""));
  if (!Number.isFinite(num) || num < 0) {
    return "Varies";
  }
  if (num === 0) {
    return "Free";
  }
  return formatPerMillionValue(num);
}

export function compareTokenPrices(a: string, b: string): number {
  const aValue = perMillionFromTokenString(a);
  const bValue = perMillionFromTokenString(b);
  if (aValue === null && bValue === null) {
    return 0;
  }
  if (aValue === null) {
    return 1;
  }
  if (bValue === null) {
    return -1;
  }
  return aValue - bValue;
}

export function formatPct(pct: number): string {
  return `${(pct * 100).toFixed(1)}%`;
}

/**
 * Display-only free-tier badge; uses current pricing only (no price history).
 * A transient API glitch could briefly show the badge on paid models until the next build.
 */
export function isFreeTierModel(
  modelId: string,
  pricing: { prompt: string; completion: string },
): boolean {
  if (modelId.endsWith(":free") || modelId === "openrouter/free") {
    return true;
  }
  return (
    parseTokenPrice(pricing.prompt).kind === "free" &&
    parseTokenPrice(pricing.completion).kind === "free"
  );
}

export function providerFromModelId(modelId: string): string {
  const slash = modelId.indexOf("/");
  if (slash === -1) {
    return modelId;
  }
  return modelId.slice(0, slash);
}

export function pricingFieldLabel(field: string): string {
  const labels: Record<string, string> = {
    prompt: "Prompt",
    completion: "Completion",
    image: "Image",
    request: "Request",
    internal_reasoning: "Reasoning",
    input_cache_read: "Cache read",
    input_cache_write: "Cache write",
    web_search: "Web search",
  };
  return labels[field] ?? field;
}
