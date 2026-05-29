import { Link } from "react-router-dom";

interface PriceDropBannerProps {
  count: number;
}

export function PriceDropBanner({ count }: PriceDropBannerProps) {
  if (count === 0) {
    return null;
  }
  return (
    <div className="banner" role="status">
      <span>
        <strong>{count}</strong> significant price{" "}
        {count === 1 ? "decrease" : "decreases"} since the last snapshot
      </span>
      <Link to="/drops">View drops →</Link>
    </div>
  );
}
