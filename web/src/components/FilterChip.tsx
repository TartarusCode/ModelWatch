interface FilterChipProps {
  label: string;
  active: boolean;
  onToggle: () => void;
}

export function FilterChip({ label, active, onToggle }: FilterChipProps) {
  return (
    <button
      type="button"
      className={`filter-chip${active ? " filter-chip--active" : ""}`}
      onClick={onToggle}
      aria-pressed={active}
    >
      {label}
    </button>
  );
}
