import { describe, expect, it } from "vitest";
import type { PricingSchedule } from "../types";
import { hasBenchmarkData } from "./data";
import {
  activeWindowRate,
  changeFieldLabel,
  formatPerMillion,
  formatPerMillionUsd,
  formatScheduleRange,
  formatSignedPerMillionUsd,
  isDiscountedNow,
  isFreeTierModel,
  localWindowLabel,
  parseTokenPrice,
  scheduleFieldTiers,
  scheduleTierGroups,
  scheduleTooltip,
  standardPricePerToken,
  windowIsActive,
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

describe("pricing schedule", () => {
  const schedule: PricingSchedule = {
    standard: { prompt: "0.0000003", completion: "0.0000012" },
    minimum: { prompt: "0.00000015", completion: "0.0000006" },
    rates: {
      prompt: ["0.00000015", "0.0000003"],
      completion: ["0.0000006", "0.0000012"],
    },
    windows: [
      {
        label: "Sat–Sun all day UTC",
        utc_days: ["saturday", "sunday"],
        utc_start: null,
        utc_end: null,
        rates: { prompt: "0.00000015", completion: "0.0000006" },
      },
      {
        label: "Mon–Fri 01:00–04:00 UTC",
        utc_days: ["monday", "tuesday", "wednesday", "thursday", "friday"],
        utc_start: 100,
        utc_end: 400,
        rates: { prompt: "0.0000003", completion: "0.0000012" },
      },
    ],
  };

  it("reads the standard and discounted rate per million", () => {
    expect(scheduleFieldTiers(schedule, "prompt")).toEqual({
      standard: 0.3,
      minimum: 0.15,
    });
  });

  it("returns null without a schedule or when every rate matches", () => {
    expect(scheduleFieldTiers(null, "prompt")).toBeNull();
    expect(
      scheduleFieldTiers(
        { ...schedule, minimum: { prompt: "0.0000003" } },
        "prompt",
      ),
    ).toBeNull();
  });

  it("renders a range instead of a point", () => {
    expect(formatScheduleRange(schedule, "prompt")).toBe("$0.15–$0.30/M");
    expect(formatScheduleRange(schedule, "completion")).toBe("$0.60–$1.20/M");
    expect(formatScheduleRange(schedule, "web_search")).toBeNull();
    expect(formatScheduleRange(null, "prompt")).toBeNull();
  });

  it("sorts on the standard rate, not the active window", () => {
    const pricing = { prompt: "0.00000015", completion: "0.0000006" };
    expect(standardPricePerToken(pricing, schedule, "prompt")).toBe(
      "0.0000003",
    );
    expect(standardPricePerToken(pricing, null, "prompt")).toBe("0.00000015");
  });

  it("finds the window that applies right now", () => {
    const peak = new Date("2026-09-21T02:00:00Z"); // Monday 02:00 UTC
    const weekend = new Date("2026-09-19T12:00:00Z"); // Saturday 12:00 UTC
    const gap = new Date("2026-09-21T12:00:00Z"); // Monday 12:00 UTC

    expect(windowIsActive(schedule.windows[1], peak)).toBe(true);
    expect(windowIsActive(schedule.windows[0], peak)).toBe(false);
    expect(activeWindowRate(schedule, "prompt", peak)).toBe(0.3);
    expect(isDiscountedNow(schedule, "prompt", peak)).toBe(false);
    expect(activeWindowRate(schedule, "prompt", weekend)).toBe(0.15);
    expect(isDiscountedNow(schedule, "prompt", weekend)).toBe(true);
    expect(activeWindowRate(schedule, "prompt", gap)).toBeNull();
    expect(isDiscountedNow(schedule, "prompt", gap)).toBe(false);
  });

  it("labels windows in local time", () => {
    expect(localWindowLabel(schedule.windows[0])).toBe("Sat–Sun all day");
    expect(localWindowLabel(schedule.windows[1])).toMatch(
      /^Mon–Fri \d{2}:\d{2}–\d{2}:\d{2}$/,
    );
  });

  it("groups windows by the rate they charge", () => {
    const groups = scheduleTierGroups(schedule);

    expect(groups.map((group) => group.prompt)).toEqual([0.15, 0.3]);
    expect(groups[0].windows).toEqual(["Sat–Sun all day"]);
    expect(groups[1].windows[0]).toMatch(/^Mon–Fri /);
  });

  it("summarises the schedule for a tooltip", () => {
    const tooltip = scheduleTooltip(schedule);

    expect(tooltip).toContain("$0.15/M in");
    expect(tooltip).toContain("$1.20/M out");
    expect(scheduleTooltip(null)).toBeNull();
  });
});

describe("changeFieldLabel", () => {
  it("names standard changes by field only", () => {
    expect(changeFieldLabel("prompt")).toBe("Prompt");
    expect(changeFieldLabel("prompt", null)).toBe("Prompt");
  });

  it("marks tiered changes", () => {
    expect(changeFieldLabel("prompt", "offpeak")).toBe("Prompt (off-peak)");
    expect(changeFieldLabel("input_cache_read", "offpeak")).toBe(
      "Cache read (off-peak)",
    );
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
