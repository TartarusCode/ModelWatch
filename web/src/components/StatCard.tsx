import { Link } from "react-router-dom";

interface StatCardProps {
  label: string;
  value: string;
  hint?: string;
  variant?: "default" | "accent" | "success";
  to?: string;
}

export function StatCard({
  label,
  value,
  hint,
  variant = "default",
  to,
}: StatCardProps) {
  const className = `stat-card stat-card--${variant}${to ? " stat-card--link" : ""}`;
  const content = (
    <>
      <span className="stat-card__label">{label}</span>
      <span className="stat-card__value">{value}</span>
      {hint ? <span className="stat-card__hint">{hint}</span> : null}
    </>
  );

  if (to) {
    return (
      <Link to={to} className={className}>
        {content}
      </Link>
    );
  }

  return <div className={className}>{content}</div>;
}
