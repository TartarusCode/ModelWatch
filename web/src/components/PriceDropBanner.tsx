import { Link } from "react-router-dom";
import type { ReactNode } from "react";

interface PriceDropBannerProps {
  freshCount: number;
  totalCount: number;
}

export function PriceDropBanner({
  freshCount,
  totalCount,
}: PriceDropBannerProps) {
  if (totalCount === 0) {
    return null;
  }

  let content: ReactNode;
  if (freshCount > 0 && freshCount === totalCount) {
    content = (
      <>
        <strong>{freshCount}</strong> new price{" "}
        {freshCount === 1 ? "decrease" : "decreases"} today
      </>
    );
  } else if (freshCount > 0) {
    content = (
      <>
        <strong>{freshCount}</strong> new price{" "}
        {freshCount === 1 ? "decrease" : "decreases"} today — {totalCount}{" "}
        active in total
      </>
    );
  } else {
    content = (
      <>
        <strong>{totalCount}</strong> price{" "}
        {totalCount === 1 ? "decrease" : "decreases"} still active
      </>
    );
  }

  return (
    <Link to="/drops" className="drop-alert">
      <span className="drop-alert__icon" aria-hidden>
        ↓
      </span>
      <span className="drop-alert__content">{content}</span>
      <span className="drop-alert__cta">View all →</span>
    </Link>
  );
}
