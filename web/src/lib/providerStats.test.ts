import { describe, expect, it } from "vitest";
import {
  formatUptime,
  mergeProviderRows,
  normalizeProviderKey,
} from "./providerStats";

describe("normalizeProviderKey", () => {
  it("matches slug and spaced provider names", () => {
    expect(normalizeProviderKey("nex-agi")).toBe("nexagi");
    expect(normalizeProviderKey("Nex AGI")).toBe("nexagi");
    expect(normalizeProviderKey("DeepInfra")).toBe("deepinfra");
  });
});

describe("mergeProviderRows", () => {
  it("joins effective pricing and list endpoints for Nex AGI", () => {
    const rows = mergeProviderRows(
      {
        provider_summaries: [
          {
            provider_name: "Nex AGI",
            provider_slug: "nex-agi",
            effective_input_price: 0.25,
            effective_output_price: 1.0,
            cache_hit_rate: 0,
            total_tokens: 1000,
          },
        ],
      },
      [
        {
          provider_name: "Nex AGI",
          name: "Nex AGI | nex-agi/nex-n2-pro",
          pricing: {
            prompt: "0.00000025",
            completion: "0.000001",
          },
        },
      ],
    );

    expect(rows).toHaveLength(1);
    expect(rows[0]?.providerName).toBe("Nex AGI");
    expect(rows[0]?.listPrompt).toBe("0.00000025");
    expect(rows[0]?.effectiveInputPrice).toBe(0.25);
  });
});

describe("formatUptime", () => {
  it("renders OpenRouter's percentage as-is", () => {
    expect(formatUptime(99.37918640744977)).toBe("99.4%");
    expect(formatUptime(100)).toBe("100.0%");
    expect(formatUptime(0.4)).toBe("0.4%");
  });

  it("renders a dash when uptime is missing", () => {
    expect(formatUptime(null)).toBe("—");
    expect(formatUptime(undefined)).toBe("—");
    expect(formatUptime(Number.NaN)).toBe("—");
  });
});
