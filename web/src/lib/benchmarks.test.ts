import { describe, expect, it } from "vitest";
import {
  formatMetricValue,
  getAaSummaryScores,
  parseArtificialAnalysisRecords,
} from "./benchmarks";

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

  it("keeps a partial summary when only some indices exist", () => {
    const scores = getAaSummaryScores(
      {
        artificial_analysis: [],
        artificial_analysis_summary: {
          intelligence_index: 39.5,
          coding_index: null,
          agentic_index: null,
          intelligence_percentile: 79,
          variant_name: "DeepSeek V4.1 Flash (Reasoning, Max Effort)",
        },
      },
      "deepseek/deepseek-v4.1-flash",
    );

    expect(scores?.intelligence).toBe(39.5);
    expect(scores?.intelligencePercentile).toBe(79);
    expect(scores?.coding).toBeUndefined();
    expect(scores?.agentic).toBeUndefined();
    expect(scores?.variantName).toBe("DeepSeek V4.1 Flash (Reasoning, Max Effort)");
  });

  it("keeps a partial index set from raw records", () => {
    const scores = getAaSummaryScores(
      {
        artificial_analysis: [
          {
            aa_slug: "deepseek-v4-1-flash",
            aa_name: "DeepSeek V4.1 Flash (Reasoning, Max Effort)",
            heuristic_openrouter_slug: "deepseek/deepseek-v4.1-flash",
            benchmark_data: {
              evaluations: {
                artificial_analysis_intelligence_index: 39.5,
                artificial_analysis_coding_index: null,
                artificial_analysis_agentic_index: null,
              },
            },
            percentiles: { intelligence_percentile: 79 },
          },
        ],
        artificial_analysis_summary: null,
      },
      "deepseek/deepseek-v4.1-flash",
    );

    expect(scores?.intelligence).toBe(39.5);
    expect(scores?.coding).toBeUndefined();
    expect(scores?.variantShort).toBe("Reasoning, Max Effort");
  });

  it("returns undefined when no index is present", () => {
    const scores = getAaSummaryScores(
      {
        artificial_analysis: [],
        artificial_analysis_summary: {
          intelligence_index: null,
          coding_index: null,
          agentic_index: null,
        },
      },
      "vendor/model",
    );

    expect(scores).toBeUndefined();
  });
});

describe("formatMetricValue", () => {
  it("renders 0-1 benchmark metrics as percentages", () => {
    expect(formatMetricValue("hle", 0.392)).toBe("39.2%");
    expect(formatMetricValue("lcr", 0.84)).toBe("84.0%");
    expect(formatMetricValue("scicode", 0.519)).toBe("51.9%");
    expect(formatMetricValue("critpt", 0.143)).toBe("14.3%");
    expect(formatMetricValue("aa_omniscience_accuracy", 0.464)).toBe("46.4%");
    expect(formatMetricValue("gdpval_aa", 0.55)).toBe("55.0%");
  });

  it("leaves larger scales alone and dashes missing metrics", () => {
    expect(formatMetricValue("artificial_analysis_intelligence_index", 39.5)).toBe("39.5");
    expect(formatMetricValue("hle", null)).toBe("—");
    expect(formatMetricValue("hle", undefined)).toBe("—");
  });
});
