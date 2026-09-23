export type ChangeStatus = "active" | "recovered" | "settled";

/**
 * One-line definitions of what each change status means.
 *
 * They are shared by the tooltips on the status pills and the notes under the
 * section headings on /changes, so the two never drift apart.
 */
export const CHANGE_STATUS_DEFINITIONS: Record<ChangeStatus, string> = {
  active:
    "Still in effect — the new price has not reverted and has not held for 7 days yet.",
  recovered:
    "The price moved back past its starting level, so the change did not stick.",
  settled:
    "The new price held for 7 days without reverting, so it is the baseline now.",
};

const ALL_DEFINITIONS: Record<string, string | undefined> =
  CHANGE_STATUS_DEFINITIONS;

export function changeStatusDefinition(status: string): string | undefined {
  return ALL_DEFINITIONS[status];
}
