import { describe, expect, it } from "vitest";
import { dropRecordsLast24Hours } from "./priceDrops";

describe("priceDrops", () => {
  it("returns only events from the last 24 hours", () => {
    const now = Date.now();
    const recent = new Date(now - 60 * 60 * 1000).toISOString();
    const old = new Date(now - 48 * 60 * 60 * 1000).toISOString();
    const records = dropRecordsLast24Hours([
      {
        detected_at: recent,
        model_id: "acme/recent",
        field: "prompt",
        old_per_million_usd: "2.000000",
        new_per_million_usd: "1.000000",
        pct_drop: 0.5,
        saved_per_million_usd: "1.000000",
      },
      {
        detected_at: old,
        model_id: "acme/old",
        field: "prompt",
        old_per_million_usd: "2.000000",
        new_per_million_usd: "1.000000",
        pct_drop: 0.5,
        saved_per_million_usd: "1.000000",
      },
    ]);

    expect(records.map((record) => record.model_id)).toEqual(["acme/recent"]);
  });
});
