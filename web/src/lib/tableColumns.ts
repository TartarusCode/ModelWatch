import type { VisibilityState } from "@tanstack/react-table";

export interface TableColumnOption {
  id: string;
  label: string;
  required?: boolean;
}

export const MODEL_TABLE_COLUMNS: TableColumnOption[] = [
  { id: "name", label: "Model", required: true },
  { id: "provider", label: "Provider" },
  { id: "prompt", label: "Prompt" },
  { id: "completion", label: "Completion" },
  { id: "context", label: "Context" },
  { id: "intelligence", label: "Intel" },
  { id: "coding", label: "Coding" },
  { id: "agentic", label: "Agentic" },
];

const STORAGE_KEY = "modelwatch.table.columnVisibility";

export function loadColumnVisibility(): VisibilityState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return {};
    }
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
      return {};
    }
    const visibility: VisibilityState = {};
    for (const [key, value] of Object.entries(parsed)) {
      if (typeof value === "boolean") {
        visibility[key] = value;
      }
    }
    return visibility;
  } catch {
    return {};
  }
}

export function saveColumnVisibility(visibility: VisibilityState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(visibility));
  } catch {
    // ignore quota / private mode
  }
}

export function isColumnVisible(
  visibility: VisibilityState,
  columnId: string,
): boolean {
  return visibility[columnId] !== false;
}

export function toggleColumnVisibility(
  visibility: VisibilityState,
  columnId: string,
  visible: boolean,
): VisibilityState {
  if (visible) {
    const next = { ...visibility };
    delete next[columnId];
    return next;
  }
  return { ...visibility, [columnId]: false };
}

export function resetColumnVisibility(): VisibilityState {
  return {};
}
