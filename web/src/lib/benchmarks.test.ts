import { describe, expect, it } from "vitest";
import { getAaSummaryScores, parseArtificialAnalysisRecords } from "./benchmarks";

describe("benchmarks", () => {
  it("parses artificial analysis records without casting", () => {
    const records = parseArtificialAnalysisRecords([
      {
        aa_slug: "demo",
        benchmark_data: {
          evaluations: {
            artificial_analysis_intelligence_index: 40,
            artificial_analysis_coding_index: 35,
            artificial_analysis_agentic_index: 50,
          },
        },
      },
    ]);

    expect(records).toHaveLength(1);
    expect(records[0].aa_slug).toBe("demo");
  });

  it("returns AA summary scores from summary payload", () => {
    const scores = getAaSummaryScores(
      {
        artificial_analysis: [],
        artificial_analysis_summary: {
          intelligence_index: 46.5,
          coding_index: 38.7,
          agentic_index: 61.3,
        },
      },
      "vendor/model",
    );

    expect(scores?.intelligence).toBe(46.5);
    expect(scores?.coding).toBe(38.7);
    expect(scores?.agentic).toBe(61.3);
  });
});
