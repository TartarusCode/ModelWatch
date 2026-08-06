export function recentEventsInDays<T extends { detected_at: string }>(
  events: T[],
  days: number,
): T[] {
  const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
  return events
    .filter((event) => new Date(event.detected_at).getTime() >= cutoff)
    .sort(
      (left, right) =>
        new Date(right.detected_at).getTime() -
        new Date(left.detected_at).getTime(),
    );
}
