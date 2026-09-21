import type { ModelPricing, PricingSchedule, PricingScheduleWindow } from "../types";

export type ParsedTokenPrice =
  | { kind: "free" }
  | { kind: "variable" }
  | { kind: "priced"; perMillion: number };

export function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function parseTokenPrice(perToken: string): ParsedTokenPrice {
  const value = Number.parseFloat(perToken);
  if (Number.isNaN(value) || value < 0) {
    return { kind: "variable" };
  }
  if (value === 0) {
    return { kind: "free" };
  }
  return { kind: "priced", perMillion: value * 1_000_000 };
}

export function perMillionFromTokenString(perToken: string): number | null {
  const parsed = parseTokenPrice(perToken);
  if (parsed.kind === "priced") {
    return parsed.perMillion;
  }
  return null;
}

/** Above this $/M, web_search is shown as $/search (catalog unit). */
export const WEB_SEARCH_PER_SEARCH_THRESHOLD_PER_MILLION = 1;

function formatUsdAmount(amount: number): string {
  if (amount < 0.01) {
    return `$${amount.toFixed(4)}`;
  }
  if (amount < 1) {
    return `$${amount.toFixed(3)}`;
  }
  return `$${amount.toFixed(2)}`;
}

function formatPerMillionValue(perMillion: number): string {
  return `${formatUsdAmount(perMillion)}/M`;
}

function formatPerSearchValue(perSearch: number): string {
  return `${formatUsdAmount(perSearch)}/search`;
}

export function usesWebSearchPerSearchDisplay(perMillion: number): boolean {
  return perMillion >= WEB_SEARCH_PER_SEARCH_THRESHOLD_PER_MILLION;
}

function formatPriceValue(perMillion: number, field?: string): string {
  if (field === "web_search" && usesWebSearchPerSearchDisplay(perMillion)) {
    return formatPerSearchValue(perMillion / 1_000_000);
  }
  return formatPerMillionValue(perMillion);
}

export function formatPerMillion(perToken: string, field?: string): string {
  const parsed = parseTokenPrice(perToken);
  if (parsed.kind === "free") {
    return "Free";
  }
  if (parsed.kind === "variable") {
    return "Varies";
  }
  return formatPriceValue(parsed.perMillion, field);
}

export function formatPerMillionUsd(
  value: string | number | null | undefined,
  field?: string,
): string {
  const num =
    typeof value === "number" ? value : Number.parseFloat(String(value ?? ""));
  if (!Number.isFinite(num) || num < 0) {
    return "Varies";
  }
  if (num === 0) {
    return "Free";
  }
  return formatPriceValue(num, field);
}

export function compareTokenPrices(a: string, b: string): number {
  const aValue = perMillionFromTokenString(a);
  const bValue = perMillionFromTokenString(b);
  if (aValue === null && bValue === null) {
    return 0;
  }
  if (aValue === null) {
    return 1;
  }
  if (bValue === null) {
    return -1;
  }
  return aValue - bValue;
}

export function formatPct(pct: number): string {
  return `${(pct * 100).toFixed(1)}%`;
}

export function formatSignedPct(pct: number): string {
  const abs = formatPct(Math.abs(pct));
  if (pct > 0) {
    return `+${abs}`;
  }
  if (pct < 0) {
    return `−${abs}`;
  }
  return abs;
}

export function formatSignedPerMillionUsd(
  value: string | number | null | undefined,
  field?: string,
): string {
  const num =
    typeof value === "number" ? value : Number.parseFloat(String(value ?? ""));
  if (!Number.isFinite(num)) {
    return "Varies";
  }
  const formatted = formatPerMillionUsd(Math.abs(num), field);
  if (num > 0) {
    return `+${formatted}`;
  }
  if (num < 0) {
    return `−${formatted}`;
  }
  return formatted;
}

/**
 * Display-only free-tier badge; uses current pricing only (no price history).
 * A transient API glitch could briefly show the badge on paid models until the next build.
 */
export function isFreeTierModel(
  modelId: string,
  pricing: { prompt: string; completion: string },
): boolean {
  if (modelId.endsWith(":free") || modelId === "openrouter/free") {
    return true;
  }
  return (
    parseTokenPrice(pricing.prompt).kind === "free" &&
    parseTokenPrice(pricing.completion).kind === "free"
  );
}

export function providerFromModelId(modelId: string): string {
  const slash = modelId.indexOf("/");
  if (slash === -1) {
    return modelId;
  }
  return modelId.slice(0, slash);
}

export function pricingFieldLabel(field: string): string {
  const labels: Record<string, string> = {
    prompt: "Prompt",
    completion: "Completion",
    image: "Image",
    request: "Request",
    internal_reasoning: "Reasoning",
    input_cache_read: "Cache read",
    input_cache_write: "Cache write",
    web_search: "Web search",
  };
  return labels[field] ?? field;
}

const TIER_LABELS: Record<string, string> = { offpeak: "off-peak" };

/** "Prompt (off-peak)" for tiered changes, "Prompt" for standard ones. */
export function changeFieldLabel(field: string, tier?: string | null): string {
  const label = pricingFieldLabel(field);
  if (!tier) {
    return label;
  }
  return `${label} (${TIER_LABELS[tier] ?? tier})`;
}

export interface ScheduleFieldTiers {
  /** Rate outside any discount window, USD per 1M tokens. */
  standard: number;
  /** Cheapest scheduled rate, USD per 1M tokens. */
  minimum: number;
}

/**
 * Standard vs. discounted rate for a scheduled field, or null when the model
 * has no schedule covering that field. Models with time-of-day pricing report
 * whichever window is active right now, so the headline price alone cannot
 * tell you whether the rate card actually changed.
 */
export function scheduleFieldTiers(
  schedule: PricingSchedule | null | undefined,
  field: string,
): ScheduleFieldTiers | null {
  if (!schedule) {
    return null;
  }
  const standard = perMillionFromTokenString(schedule.standard[field] ?? "");
  const minimum = perMillionFromTokenString(schedule.minimum[field] ?? "");
  if (standard === null || minimum === null || standard === minimum) {
    return null;
  }
  return { standard, minimum };
}

const DAY_ABBREVIATIONS: Record<string, string> = {
  monday: "Mon",
  tuesday: "Tue",
  wednesday: "Wed",
  thursday: "Thu",
  friday: "Fri",
  saturday: "Sat",
  sunday: "Sun",
};
const WEEKDAY_ORDER = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
];
const WEEKDAYS = new Set(WEEKDAY_ORDER.slice(0, 5));

function formatDays(days: string[] | null): string {
  if (!days || days.length === 0 || days.length === 7) {
    return "Every day";
  }
  const set = new Set(days.map((day) => day.toLowerCase()));
  if (set.size === WEEKDAYS.size && [...WEEKDAYS].every((day) => set.has(day))) {
    return "Mon–Fri";
  }
  if (set.size === 2 && set.has("saturday") && set.has("sunday")) {
    return "Sat–Sun";
  }
  return WEEKDAY_ORDER.filter((day) => set.has(day))
    .map((day) => DAY_ABBREVIATIONS[day])
    .join(", ");
}

function clockToLocalTime(hhmm: number, now: Date): string {
  const hours = Math.floor(hhmm / 100);
  const minutes = hhmm % 100;
  const asUtc = new Date(
    Date.UTC(
      now.getUTCFullYear(),
      now.getUTCMonth(),
      now.getUTCDate(),
      hours,
      minutes,
    ),
  );
  return `${String(asUtc.getHours()).padStart(2, "0")}:${String(asUtc.getMinutes()).padStart(2, "0")}`;
}

/**
 * Window label in the viewer's local time (the API publishes UTC HHMM clock
 * values, which are unreadable for anyone not living in UTC).
 */
export function localWindowLabel(
  window: PricingScheduleWindow,
  now: Date = new Date(),
): string {
  const days = formatDays(window.utc_days);
  if (window.utc_start === null && window.utc_end === null) {
    return `${days} all day`;
  }
  const start = clockToLocalTime(window.utc_start ?? 0, now);
  const end = window.utc_end ? clockToLocalTime(window.utc_end, now) : "24:00";
  return `${days} ${start}–${end}`;
}

function utcDayName(now: Date): string {
  return WEEKDAY_ORDER[(now.getUTCDay() + 6) % 7];
}

export function windowIsActive(
  window: PricingScheduleWindow,
  now: Date = new Date(),
): boolean {
  if (
    window.utc_days &&
    !window.utc_days
      .map((day) => day.toLowerCase())
      .includes(utcDayName(now))
  ) {
    return false;
  }
  if (window.utc_start === null && window.utc_end === null) {
    return true;
  }
  const hhmm = now.getUTCHours() * 100 + now.getUTCMinutes();
  const start = window.utc_start ?? 0;
  const end = window.utc_end || 2400;
  return end > start ? hhmm >= start && hhmm < end : hhmm >= start || hhmm < end;
}

/** Rate the schedule charges for `field` right now, USD per 1M tokens. */
export function activeWindowRate(
  schedule: PricingSchedule | null | undefined,
  field: string,
  now: Date = new Date(),
): number | null {
  if (!schedule) {
    return null;
  }
  for (const window of schedule.windows) {
    if (!windowIsActive(window, now)) {
      continue;
    }
    const rate = perMillionFromTokenString(window.rates[field] ?? "");
    if (rate !== null) {
      return rate;
    }
  }
  return null;
}

/** True while a discount window is in effect for the field. */
export function isDiscountedNow(
  schedule: PricingSchedule | null | undefined,
  field: string,
  now: Date = new Date(),
): boolean {
  const active = activeWindowRate(schedule, field, now);
  const tiers = scheduleFieldTiers(schedule, field);
  if (active === null || tiers === null) {
    return false;
  }
  return active < tiers.standard;
}

function formatCompactUsd(amount: number): string {
  const trimmed = amount
    .toFixed(4)
    .replace(/0+$/, "")
    .replace(/\.$/, "");
  const [whole, fraction = ""] = trimmed.split(".");
  return `$${whole}.${fraction.padEnd(2, "0")}`;
}

/**
 * "$0.15–$0.30/M" for a scheduled field, or null when the field is not
 * scheduled. A price that moves with the clock is a range, not a point.
 */
export function formatScheduleRange(
  schedule: PricingSchedule | null | undefined,
  field: string,
): string | null {
  if (field === "web_search") {
    return null;
  }
  const tiers = scheduleFieldTiers(schedule, field);
  if (tiers === null) {
    return null;
  }
  return `${formatCompactUsd(tiers.minimum)}–${formatCompactUsd(tiers.standard)}/M`;
}

/**
 * Per-token price string to sort by: the standard rate for scheduled models so
 * ordering does not move as windows come and go.
 */
export function standardPricePerToken(
  pricing: ModelPricing,
  schedule: PricingSchedule | null | undefined,
  field: "prompt" | "completion",
): string {
  return schedule?.standard?.[field] ?? pricing[field] ?? "";
}

export interface ScheduleTierGroup {
  prompt: number;
  completion: number;
  windows: string[];
}

/** Windows grouped by the rate they charge, cheapest first, local time. */
export function scheduleTierGroups(
  schedule: PricingSchedule | null | undefined,
  now: Date = new Date(),
): ScheduleTierGroup[] {
  if (!schedule) {
    return [];
  }
  const groups = new Map<string, ScheduleTierGroup>();
  for (const window of schedule.windows) {
    const prompt = perMillionFromTokenString(window.rates.prompt ?? "");
    const completion = perMillionFromTokenString(window.rates.completion ?? "");
    if (prompt === null || completion === null) {
      continue;
    }
    const key = `${prompt}|${completion}`;
    const group = groups.get(key) ?? { prompt, completion, windows: [] };
    group.windows.push(localWindowLabel(window, now));
    groups.set(key, group);
  }
  return [...groups.values()].sort((a, b) => a.prompt - b.prompt);
}

/** One-line summary of a schedule for a tooltip (local time). */
export function scheduleTooltip(
  schedule: PricingSchedule | null | undefined,
  now: Date = new Date(),
): string | null {
  const groups = scheduleTierGroups(schedule, now);
  if (groups.length === 0) {
    return null;
  }
  const parts = groups.map(
    (group) =>
      `${formatCompactUsd(group.prompt)}/M in · ${formatCompactUsd(group.completion)}/M out — ${group.windows.join(", ")}`,
  );
  return `Time-of-day pricing, local time: ${parts.join(" · ")}`;
}
