interface StatCardProps {
  label: string;
  value: string;
  hint?: string;
  variant?: "default" | "accent" | "success";
}

export function StatCard({
  label,
  value,
  hint,
  variant = "default",
}: StatCardProps) {
  return (
    <div className={`stat-card stat-card--${variant}`}>
      <span className="stat-card__label">{label}</span>
      <span className="stat-card__value">{value}</span>
      {hint ? <span className="stat-card__hint">{hint}</span> : null}
    </div>
  );
}
