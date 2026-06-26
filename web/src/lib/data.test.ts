import { afterEach, describe, expect, it, vi } from "vitest";
import { loadSiteData } from "./data";

describe("loadSiteData", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads site artifacts from public data paths", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url.endsWith("meta.json")) {
        return new Response(
          JSON.stringify({
            generated_at: "2026-06-25T12:00:00Z",
            model_count: 1,
            build_duration_seconds: 1,
            benchmark_errors: 0,
            benchmark_empty: 0,
          }),
        );
      }
      if (url.endsWith("models.json")) {
        return new Response(
          JSON.stringify({
            generated_at: "2026-06-25T12:00:00Z",
            models: [],
          }),
        );
      }
      if (url.endsWith("price-drops.json")) {
        return new Response(
          JSON.stringify({
            generated_at: "2026-06-25T12:00:00Z",
            thresholds: { min_pct: 0.1, min_saved_per_million_usd: 0.05 },
            drops: [],
          }),
        );
      }
      if (url.endsWith("new-models.json")) {
        return new Response(
          JSON.stringify({
            generated_at: "2026-06-25T12:00:00Z",
            models: [],
          }),
        );
      }
      if (url.endsWith("price-history.json")) {
        return new Response(
          JSON.stringify({
            generated_at: "2026-06-25T12:00:00Z",
            models: {},
          }),
        );
      }
      if (url.endsWith(".jsonl")) {
        return new Response("");
      }
      return new Response("", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const data = await loadSiteData();

    expect(data.meta.model_count).toBe(1);
    expect(data.models.models).toEqual([]);
    expect(data.priceEvents).toEqual([]);
  });
});
