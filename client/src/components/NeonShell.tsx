import type { ReactNode } from "react";

/** Cyberpunk neon wrapper — Developed by Suckbob | Monster AI */
export function NeonShell({
  title,
  subtitle,
  children,
  badge,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  badge?: string;
}) {
  return (
    <div className="monster-neon-page flex-1 overflow-auto p-4 md:p-6 space-y-6">
      <div className="scanlines pointer-events-none fixed inset-0 z-[1]" aria-hidden />
      <header className="relative z-[2] flex flex-wrap items-end justify-between gap-3 border-b border-[var(--neon-border)] pb-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-wider text-[var(--neon-cyan)] neon-text-glow">
            {title}
          </h1>
          {subtitle && (
            <p className="text-sm text-[var(--neon-muted)] mt-1 max-w-2xl">{subtitle}</p>
          )}
        </div>
        {badge && (
          <span className="text-xs text-[var(--neon-muted)] border border-[var(--neon-border)] rounded-lg px-3 py-1">
            {badge}
          </span>
        )}
      </header>
      <div className="relative z-[2]">{children}</div>
    </div>
  );
}

export function NeonPanel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`neon-panel rounded-xl border border-[var(--neon-border)] bg-[var(--neon-panel)] p-4 md:p-5 shadow-[0_0_24px_rgba(0,245,255,0.08)] ${className}`}
    >
      {children}
    </div>
  );
}