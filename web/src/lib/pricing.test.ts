import { describe, expect, it } from "vitest";
import { hasBenchmarkData } from "./data";
import {
  formatPerMillion,
  formatPerMillionUsd,
  formatSignedPerMillionUsd,
  isFreeTierModel,
  parseTokenPrice,
} from "./pricing";

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

  it("formats high web_search prices per search", () => {
    expect(formatPerMillion("0.014", "web_search")).toBe("$0.014/search");
    expect(formatPerMillion("0.01", "web_search")).toBe("$0.010/search");
    expect(formatPerMillionUsd(14000, "web_search")).toBe("$0.014/search");
    expect(formatSignedPerMillionUsd(-4000, "web_search")).toBe(
      "−$0.0040/search",
    );
  });

  it("keeps low web_search prices as per million", () => {
    expect(formatPerMillion("0.0000005", "web_search")).toBe("$0.500/M");
  });

  it("does not use per-search formatting for other fields", () => {
    expect(formatPerMillion("0.014", "prompt")).toBe("$14000.00/M");
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
