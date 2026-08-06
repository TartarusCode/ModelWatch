import {
  pickAaRecord,
  shortVariantLabel,
  type ModelAaVariantSelection,
} from "../lib/aaVariants";
import type { ArtificialAnalysisRecord } from "../lib/benchmarks";

interface ModelAaVariantPickerProps {
  modelId: string;
  records: ArtificialAnalysisRecord[];
  value: ModelAaVariantSelection;
  onChange: (value: ModelAaVariantSelection) => void;
}

export function ModelAaVariantPicker({
  modelId,
  records,
  value,
  onChange,
}: ModelAaVariantPickerProps) {
  const defaultRecord = pickAaRecord(records, modelId, "auto");
  const defaultLabel = shortVariantLabel(defaultRecord?.aa_name) ?? "auto";

  if (records.length <= 1) {
    return null;
  }

  return (
    <label className="aa-variant-picker">
      <span className="aa-variant-picker__label">Benchmark profile</span>
      <select
        className="select-field"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-label="Artificial Analysis benchmark profile for this model"
      >
        <option value="default">Default ({defaultLabel})</option>
        {records.map((record) => {
          const slug = record.aa_slug ?? record.aa_id;
          if (!slug) {
            return null;
          }
          return (
            <option key={slug} value={slug}>
              {record.aa_name ?? slug}
            </option>
          );
        })}
      </select>
    </label>
  );
}
