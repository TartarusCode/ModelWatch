import type { VisibilityState } from "@tanstack/react-table";
import {
  isColumnVisible,
  MODEL_TABLE_COLUMNS,
  resetColumnVisibility,
  toggleColumnVisibility,
  type TableColumnOption,
} from "../lib/tableColumns";

interface ColumnPickerProps {
  visibility: VisibilityState;
  onChange: (visibility: VisibilityState) => void;
}

function hideableColumns(): TableColumnOption[] {
  return MODEL_TABLE_COLUMNS.filter((column) => !column.required);
}

export function ColumnPicker({ visibility, onChange }: ColumnPickerProps) {
  const hiddenCount = hideableColumns().filter(
    (column) => !isColumnVisible(visibility, column.id),
  ).length;

  return (
    <details className="column-picker">
      <summary className="column-picker__trigger" aria-label="Choose visible columns">
        Columns
        {hiddenCount > 0 ? (
          <span className="column-picker__badge">{hiddenCount} hidden</span>
        ) : null}
      </summary>
      <div className="column-picker__menu" role="group" aria-label="Table columns">
        <ul className="column-picker__list">
          {hideableColumns().map((column) => {
            const visible = isColumnVisible(visibility, column.id);
            return (
              <li key={column.id}>
                <label className="column-picker__option">
                  <input
                    type="checkbox"
                    checked={visible}
                    onChange={(event) =>
                      onChange(
                        toggleColumnVisibility(
                          visibility,
                          column.id,
                          event.target.checked,
                        ),
                      )
                    }
                  />
                  <span>{column.label}</span>
                </label>
              </li>
            );
          })}
        </ul>
        <button
          type="button"
          className="column-picker__reset"
          onClick={() => onChange(resetColumnVisibility())}
        >
          Show all
        </button>
      </div>
    </details>
  );
}
