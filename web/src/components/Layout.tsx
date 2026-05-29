import { Link, NavLink, Outlet } from "react-router-dom";
import type { BuildMeta } from "../types";

interface LayoutProps {
  meta: BuildMeta | null;
  dropCount: number;
}

export function Layout({ meta, dropCount }: LayoutProps) {
  return (
    <div className="app-shell">
      <header className="site-header">
        <h1 className="site-title">
          <Link to="/">ModelWatch</Link>
        </h1>
        <nav className="site-nav">
          <NavLink
            to="/"
            end
            className={({ isActive }) => (isActive ? "active" : undefined)}
          >
            Models
          </NavLink>
          <NavLink
            to="/drops"
            className={({ isActive }) => (isActive ? "active" : undefined)}
          >
            Price drops
            {dropCount > 0 ? ` (${dropCount})` : ""}
          </NavLink>
        </nav>
      </header>
      <Outlet />
      <footer className="site-footer">
        {meta ? (
          <p>
            Last updated {new Date(meta.generated_at).toLocaleString()} ·{" "}
            {meta.model_count} models · build took{" "}
            {meta.build_duration_seconds.toFixed(0)}s
          </p>
        ) : null}
        <p className="muted">
          Unofficial dashboard. Data from{" "}
          <a href="https://openrouter.ai" target="_blank" rel="noreferrer">
            OpenRouter
          </a>
          .{" "}
          <a
            href="https://github.com/TartarusCode/ModelWatch"
            target="_blank"
            rel="noreferrer"
          >
            Source
          </a>
        </p>
      </footer>
    </div>
  );
}
