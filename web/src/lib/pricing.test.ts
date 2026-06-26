import { describe, expect, it } from "vitest";
import { hasBenchmarkData } from "./data";
import { formatPerMillion, isFreeTierModel, parseTokenPrice } from "./pricing";

describe("pricing", () => {
  it("parses positive token prices", () => {
    expect(parseTokenPrice("0.000001")).toEqual({
      kind: "priced",
      perMillion: 1,
    });
  });

  it("detects free tier models", () => {
    expect(
      isFreeTierModel("demo/model:free", {
        prompt: "0",
        completion: "0",
      }),
    ).toBe(true);
  });

  it("formats per-million prices", () => {
    expect(formatPerMillion("0.000001")).toBe("$1.00/M");
  });
});

describe("hasBenchmarkData", () => {
  it("returns true when design arena data exists", () => {
    expect(
      hasBenchmarkData({
        design_arena: null,
        design_arena_status: { status: "ok" },
        artificial_analysis: [],
        artificial_analysis_status: { status: "empty" },
        benchmark_scores_status: { status: "empty" },
      }),
    ).toBe(true);
  });
});
