export function perMillionFromTokenString(perToken: string): number {
  const value = Number.parseFloat(perToken);
  if (Number.isNaN(value)) {
    return 0;
  }
  return value * 1_000_000;
}

export function formatPerMillion(perToken: string): string {
  const perMillion = perMillionFromTokenString(perToken);
  if (perMillion === 0) {
    return "Free";
  }
  if (perMillion < 0.01) {
    return `$${perMillion.toFixed(4)}/M`;
  }
  if (perMillion < 1) {
    return `$${perMillion.toFixed(3)}/M`;
  }
  return `$${perMillion.toFixed(2)}/M`;
}

export function formatPerMillionUsd(value: string): string {
  const num = Number.parseFloat(value);
  if (Number.isNaN(num) || num === 0) {
    return "Free";
  }
  if (num < 0.01) {
    return `$${num.toFixed(4)}/M`;
  }
  if (num < 1) {
    return `$${num.toFixed(3)}/M`;
  }
  return `$${num.toFixed(2)}/M`;
}

export function formatPct(pct: number): string {
  return `${(pct * 100).toFixed(1)}%`;
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
