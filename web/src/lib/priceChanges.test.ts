import { describe, expect, it } from "vitest";
import {
  changeAgeLabel,
  countChangesByDirection,
  episodesForModel,
  filterChangesByDirection,
  isDetectedWithinHours,
  sortChangesBySeverity,
  sortChangesChronologically,
  splitChangesByFreshness,
} from "./priceChanges";
import type { PriceChangeRecord } from "../types";

function episode(
  overrides: Partial<PriceChangeRecord> & Pick<PriceChangeRecord, "detected_at">,
): PriceChangeRecord {
  return {
    model_id: "acme/model",
    field: "prompt",
    direction: "cut",
    episode_start_per_million_usd: "1.000000",
    old_per_million_usd: "1.000000",
    new_per_million_usd: "0.800000",
    pct_change: -0.2,
    delta_per_million_usd: "-0.200000",
    status: "active",
    recovered_at: null,
    recovered_per_million_usd: null,
    ...overrides,
  };
}

describe("priceChanges", () => {
  it("sorts changes by severity magnitude", () => {
    const sorted = sortChangesBySeverity([
      episode({ detected_at: "2026-07-01T00:00:00Z", pct_change: -0.1 }),
      episode({
        detected_at: "2026-07-02T00:00:00Z",
        pct_change: 0.3,
        direction: "hike",
        delta_per_million_usd: "0.300000",
      }),
    ]);

    expect(sorted[0]?.pct_change).toBe(0.3);
  });

  it("sorts changes chronologically newest first", () => {
    const sorted = sortChangesChronologically([
      episode({ detected_at: "2026-07-01T00:00:00Z", model_id: "older" }),
      episode({ detected_at: "2026-07-08T12:00:00Z", model_id: "newer" }),
      episode({ detected_at: "2026-07-05T00:00:00Z", model_id: "mid" }),
    ]);

    expect(sorted.map((d) => d.model_id)).toEqual(["newer", "mid", "older"]);
  });

  it("sorts recovered changes by recovered_at when provided", () => {
    const sorted = sortChangesChronologically(
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

  it("splits changes by freshness and handles empty input", () => {
    const now = new Date("2026-07-15T12:00:00Z");
    expect(splitChangesByFreshness([], 24, now)).toEqual({
      freshChanges: [],
      olderChanges: [],
    });

    const changes = [
      episode({ detected_at: "2026-07-15T10:00:00Z", model_id: "a/new" }),
      episode({ detected_at: "2026-07-08T10:00:00Z", model_id: "b/old" }),
    ];
    const { freshChanges, olderChanges } = splitChangesByFreshness(
      changes,
      24,
      now,
    );

    expect(freshChanges.map((d) => d.model_id)).toEqual(["a/new"]);
    expect(olderChanges.map((d) => d.model_id)).toEqual(["b/old"]);
  });

  it("labels change age for today, one day, and multi-day", () => {
    const now = new Date("2026-07-15T12:00:00Z");

    expect(
      changeAgeLabel(episode({ detected_at: "2026-07-15T08:00:00Z" }), now),
    ).toBe("Today");
    expect(
      changeAgeLabel(episode({ detected_at: "2026-07-14T11:00:00Z" }), now),
    ).toBe("1 day ago");
    expect(
      changeAgeLabel(episode({ detected_at: "2026-07-08T12:00:00Z" }), now),
    ).toBe("7 days ago");
  });

  it("filters changes by direction", () => {
    const changes = [
      episode({ detected_at: "2026-07-01T00:00:00Z", direction: "cut" }),
      episode({
        detected_at: "2026-07-02T00:00:00Z",
        direction: "hike",
        pct_change: 0.2,
        delta_per_million_usd: "0.200000",
      }),
    ];

    expect(filterChangesByDirection(changes, "all")).toHaveLength(2);
    expect(filterChangesByDirection(changes, "cut")).toHaveLength(1);
    expect(filterChangesByDirection(changes, "hike")[0]?.direction).toBe("hike");
  });

  it("counts cuts and hikes", () => {
    const counts = countChangesByDirection([
      episode({ detected_at: "2026-07-01T00:00:00Z", direction: "cut" }),
      episode({
        detected_at: "2026-07-02T00:00:00Z",
        direction: "hike",
        pct_change: 0.2,
      }),
      episode({ detected_at: "2026-07-03T00:00:00Z", direction: "cut" }),
    ]);
    expect(counts).toEqual({ cuts: 2, hikes: 1 });
  });
});
