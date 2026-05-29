import { Link } from "react-router-dom";

interface PriceDropBannerProps {
  count: number;
}

export function PriceDropBanner({ count }: PriceDropBannerProps) {
  if (count === 0) {
    return null;
  }
  return (
    <Link to="/drops" className="drop-alert">
      <span className="drop-alert__icon" aria-hidden>
        ↓
      </span>
      <span className="drop-alert__content">
        <strong>{count}</strong> significant price{" "}
        {count === 1 ? "decrease" : "decreases"} in the last 24 hours
      </span>
      <span className="drop-alert__cta">View all →</span>
    </Link>
  );
}
