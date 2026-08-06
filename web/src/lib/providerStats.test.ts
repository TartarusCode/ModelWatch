import { describe, expect, it } from "vitest";
import { mergeProviderRows, normalizeProviderKey } from "./providerStats";

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
