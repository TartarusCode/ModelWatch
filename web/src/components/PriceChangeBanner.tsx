import { Link } from "react-router-dom";
import type { ReactNode } from "react";

interface PriceChangeBannerProps {
  freshCount: number;
  totalCount: number;
  cutCount: number;
  hikeCount: number;
}

export function PriceChangeBanner({
  freshCount,
  totalCount,
  cutCount,
  hikeCount,
}: PriceChangeBannerProps) {
  if (totalCount === 0) {
    return null;
  }

  const directionSummary = (
    <>
      {cutCount > 0 ? (
        <>
          <strong>{cutCount}</strong> {cutCount === 1 ? "cut" : "cuts"}
        </>
      ) : null}
      {cutCount > 0 && hikeCount > 0 ? " · " : null}
      {hikeCount > 0 ? (
        <>
          <strong>{hikeCount}</strong> {hikeCount === 1 ? "hike" : "hikes"}
        </>
      ) : null}
    </>
  );

  let content: ReactNode;
  if (freshCount > 0 && freshCount === totalCount) {
    content = (
      <>
        {directionSummary} today
      </>
    );
  } else if (freshCount > 0) {
    content = (
      <>
        <strong>{freshCount}</strong> new today — {directionSummary} active
      </>
    );
  } else {
    content = (
      <>
        {directionSummary} still active
      </>
    );
  }

  return (
    <Link to="/changes" className="change-alert">
      <span className="change-alert__icon" aria-hidden>
        ↔
      </span>
      <span className="change-alert__content">{content}</span>
      <span className="change-alert__cta">View all →</span>
    </Link>
  );
}
