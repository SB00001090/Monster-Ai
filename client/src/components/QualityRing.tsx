/** Quality score ring — green >= 70%, red below. Developed by Suckbob */

const THRESHOLD = 0.7;

export function QualityRing({
  score,
  passed,
  size = 56,
  label,
}: {
  score?: number | null;
  passed?: boolean | null;
  size?: number;
  label?: string;
}) {
  if (score == null && passed == null) return null;

  const pct = score != null ? Math.round(score * 100) : passed ? 100 : 0;
  const ok = passed ?? (score != null && score >= THRESHOLD);
  const r = (size - 8) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;
  const color = ok ? "var(--neon-green, #39ff14)" : "var(--neon-pink, #ff2d6a)";

  return (
    <div className="inline-flex flex-col items-center gap-1" title={label}>
      <svg width={size} height={size} className="rotate-[-90deg]">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--neon-border, #1a3a4a)"
          strokeWidth={5}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={5}
          strokeDasharray={c}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      <span
        className="text-xs font-mono -mt-12 rotate-0 relative z-10"
        style={{ color }}
      >
        {pct}%
      </span>
      {label && (
        <span className="text-[10px] text-[var(--neon-muted)]">{label}</span>
      )}
    </div>
  );
}

export function qualityFromResult(result: Record<string, unknown>): {
  score?: number;
  passed?: boolean;
} {
  const q = result.quality as Record<string, unknown> | undefined;
  if (!q) return {};
  return {
    score: typeof q.score === "number" ? q.score : undefined,
    passed: typeof q.passed === "boolean" ? q.passed : undefined,
  };
}