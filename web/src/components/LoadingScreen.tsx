export function LoadingScreen() {
  return (
    <div className="loading-screen" role="status" aria-live="polite">
      <div className="loading-screen__spinner" aria-hidden />
      <p aria-label="Loading">Loading OpenRouter catalog…</p>
    </div>
  );
}
