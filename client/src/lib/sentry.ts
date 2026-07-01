/** Optional Sentry init — only when VITE_SENTRY_DSN and @sentry/react are available. */

export async function initSentry(): Promise<void> {
  const dsn = import.meta.env.VITE_SENTRY_DSN?.trim();
  if (!dsn || typeof window === "undefined") return;
  console.warn("[Sentry] @sentry/react not installed — skip error tracking");
}