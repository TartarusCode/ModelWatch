import { describe, expect, it } from "vitest";
import {
  dropAgeLabel,
  episodesForModel,
  isDetectedWithinHours,
  sortDropsBySeverity,
  sortDropsChronologically,
  splitDropsByFreshness,
} from "./priceDrops";
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

  it("sorts drops chronologically newest first", () => {
    const sorted = sortDropsChronologically([
      episode({ detected_at: "2026-07-01T00:00:00Z", model_id: "older" }),
      episode({ detected_at: "2026-07-08T12:00:00Z", model_id: "newer" }),
      episode({ detected_at: "2026-07-05T00:00:00Z", model_id: "mid" }),
    ]);

    expect(sorted.map((d) => d.model_id)).toEqual(["newer", "mid", "older"]);
  });

  it("sorts recovered drops by recovered_at when provided", () => {
    const sorted = sortDropsChronologically(
      [
        episode({
          detected_at: "2026-07-01T00:00:00Z",
          status: "recovered",
          recovered_at: "2026-07-10T00:00:00Z",
          model_id: "later-recovery",
        }),
        episode({
          detected_at: "2026-07-08T00:00:00Z",
          status: "recovered",
          recovered_at: "2026-07-09T00:00:00Z",
          model_id: "earlier-recovery",
        }),
      ],
      "recovered_at",
    );

    expect(sorted.map((d) => d.model_id)).toEqual([
      "later-recovery",
      "earlier-recovery",
    ]);
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

  it("treats exact lookback boundary as fresh", () => {
    const now = new Date("2026-07-15T12:00:00Z");
    const fresh = episode({ detected_at: "2026-07-14T12:00:00Z" });
    const older = episode({ detected_at: "2026-07-14T11:59:59Z" });

    expect(isDetectedWithinHours(fresh, 24, now)).toBe(true);
    expect(isDetectedWithinHours(older, 24, now)).toBe(false);
  });

  it("splits drops by freshness and handles empty input", () => {
    const now = new Date("2026-07-15T12:00:00Z");
    expect(splitDropsByFreshness([], 24, now)).toEqual({
      freshDrops: [],
      olderDrops: [],
    });

    const drops = [
      episode({ detected_at: "2026-07-15T10:00:00Z", model_id: "a/new" }),
      episode({ detected_at: "2026-07-08T10:00:00Z", model_id: "b/old" }),
    ];
    const { freshDrops, olderDrops } = splitDropsByFreshness(drops, 24, now);

    expect(freshDrops.map((d) => d.model_id)).toEqual(["a/new"]);
    expect(olderDrops.map((d) => d.model_id)).toEqual(["b/old"]);
  });

  it("labels drop age for today, one day, and multi-day", () => {
    const now = new Date("2026-07-15T12:00:00Z");

    expect(
      dropAgeLabel(episode({ detected_at: "2026-07-15T08:00:00Z" }), now),
    ).toBe("Today");
    expect(
      dropAgeLabel(episode({ detected_at: "2026-07-14T11:00:00Z" }), now),
    ).toBe("1 day ago");
    expect(
      dropAgeLabel(episode({ detected_at: "2026-07-08T12:00:00Z" }), now),
    ).toBe("7 days ago");
  });
});
