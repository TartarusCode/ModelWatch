import { describe, expect, it } from "vitest";
import { episodesForModel, sortDropsBySeverity } from "./priceDrops";
import type { PriceDropRecord } from "../types";

function episode(
  overrides: Partial<PriceDropRecord> & Pick<PriceDropRecord, "detected_at">,
): PriceDropRecord {
  return {
    model_id: "acme/model",
    field: "prompt",
    episode_start_per_million_usd: "1.000000",
    old_per_million_usd: "1.000000",
    new_per_million_usd: "0.800000",
    pct_drop: 0.2,
    saved_per_million_usd: "0.200000",
    status: "active",
    recovered_at: null,
    recovered_per_million_usd: null,
    ...overrides,
  };
}

describe("priceDrops", () => {
  it("sorts drops by severity", () => {
    const sorted = sortDropsBySeverity([
      episode({ detected_at: "2026-07-01T00:00:00Z", pct_drop: 0.1 }),
      episode({ detected_at: "2026-07-02T00:00:00Z", pct_drop: 0.3 }),
    ]);

    expect(sorted[0]?.pct_drop).toBe(0.3);
  });

  it("filters episodes for a model", () => {
    const episodes = episodesForModel(
      [
        episode({ detected_at: "2026-07-01T00:00:00Z" }),
        episode({
          detected_at: "2026-07-02T00:00:00Z",
          model_id: "other/model",
        }),
      ],
      "acme/model",
    );

    expect(episodes).toHaveLength(1);
    expect(episodes[0]?.model_id).toBe("acme/model");
  });
});
