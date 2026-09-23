import { describe, expect, it } from "vitest";
import {
  CHANGE_STATUS_DEFINITIONS,
  changeStatusDefinition,
} from "./changeStatus";

describe("change status definitions", () => {
  it("defines every status", () => {
    expect(Object.keys(CHANGE_STATUS_DEFINITIONS).sort()).toEqual([
      "active",
      "recovered",
      "settled",
    ]);
    for (const definition of Object.values(CHANGE_STATUS_DEFINITIONS)) {
      expect(definition.length).toBeGreaterThan(20);
    }
  });

  it("distinguishes a reversal from a change that stuck", () => {
    expect(CHANGE_STATUS_DEFINITIONS.recovered).toMatch(/moved back/i);
    expect(CHANGE_STATUS_DEFINITIONS.settled).toMatch(/7 days/);
    expect(CHANGE_STATUS_DEFINITIONS.settled).not.toMatch(/moved back/i);
    expect(CHANGE_STATUS_DEFINITIONS.recovered).not.toMatch(/7 days/);
  });

  it("looks up definitions by status and ignores unknown ones", () => {
    expect(changeStatusDefinition("settled")).toBe(
      CHANGE_STATUS_DEFINITIONS.settled,
    );
    expect(changeStatusDefinition("active")).toBe(
      CHANGE_STATUS_DEFINITIONS.active,
    );
    expect(changeStatusDefinition("nonsense")).toBeUndefined();
  });
});
