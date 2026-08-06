import { Link } from "react-router-dom";

interface NewModelBannerProps {
  count: number;
}

export function NewModelBanner({ count }: NewModelBannerProps) {
  if (count === 0) {
    return null;
  }
  return (
    <Link to="/new" className="new-model-alert">
      <span className="new-model-alert__icon" aria-hidden>
        +
      </span>
      <span className="new-model-alert__content">
        <strong>{count}</strong> new {count === 1 ? "model" : "models"} in the
        last 24 hours
      </span>
      <span className="new-model-alert__cta">View all →</span>
    </Link>
  );
}
