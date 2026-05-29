import { Link, NavLink, Outlet } from "react-router-dom";
import type { BuildMeta } from "../types";

interface LayoutProps {
  meta: BuildMeta | null;
  dropCount: number;
}

function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const diffMs = Date.now() - then;
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) {
    return "just now";
  }
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }
  return new Date(iso).toLocaleDateString();
}

export function Layout({ meta, dropCount }: LayoutProps) {
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <Link to="/" className="sidebar__logo">
            <span className="sidebar__logo-mark" aria-hidden>
              MW
            </span>
            <span className="sidebar__logo-text">ModelWatch</span>
          </Link>
        </div>
        <nav className="sidebar__nav" aria-label="Main">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `sidebar__link${isActive ? " sidebar__link--active" : ""}`
            }
          >
            <span className="sidebar__link-icon" aria-hidden>
              ⊞
            </span>
            Models
          </NavLink>
          <NavLink
            to="/drops"
            className={({ isActive }) =>
              `sidebar__link${isActive ? " sidebar__link--active" : ""}`
            }
          >
            <span className="sidebar__link-icon" aria-hidden>
              ↓
            </span>
            Price drops
            {dropCount > 0 ? (
              <span className="sidebar__badge">{dropCount}</span>
            ) : null}
          </NavLink>
        </nav>
        <div className="sidebar__footer">
          {meta ? (
            <div className="sidebar__meta">
              <span className="sidebar__meta-label">Last sync</span>
              <span className="sidebar__meta-value">
                {formatRelativeTime(meta.generated_at)}
              </span>
              <span className="sidebar__meta-sub">
                {meta.model_count.toLocaleString()} models
              </span>
            </div>
          ) : null}
          <div className="sidebar__links">
            <a
              href="https://openrouter.ai"
              target="_blank"
              rel="noreferrer"
              className="sidebar__external"
            >
              OpenRouter
            </a>
          </div>
        </div>
      </aside>
      <div className="main">
        <Outlet />
        <footer className="main-footer">
          <p>
            Unofficial dashboard — not affiliated with OpenRouter. Data refreshed
            every 30 minutes via GitHub Actions.
          </p>
        </footer>
      </div>
    </div>
  );
}
