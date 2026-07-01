import { Shield } from "lucide-react";
import type { SecuritySnapshot } from "@/hooks/useSecurityStatus";

interface Props {
  snapshot: SecuritySnapshot | null;
  onOpenSecurity: () => void;
}

function StatusDot({ status }: { status: "ok" | "warn" | "locked" | "off" }) {
  const cls =
    status === "ok"
      ? "bg-emerald-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]"
      : status === "warn"
        ? "bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.6)]"
        : status === "locked"
          ? "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]"
          : "bg-zinc-600";
  return <span className={`w-2 h-2 rounded-full shrink-0 ${cls}`} />;
}

function rowStatus(
  enabled: boolean,
  green: boolean,
  alert: boolean
): "ok" | "warn" | "locked" | "off" {
  if (!enabled) return "off";
  if (alert) return "locked";
  if (green) return "ok";
  return "warn";
}

export default function SecurityStatusBar({ snapshot, onOpenSecurity }: Props) {
  const ml = snapshot?.monsterlock;
  const cg = snapshot?.crimeguard;
  const rows = [
    {
      label: "MonsterShield",
      status: rowStatus(!!ml?.enabled, !!ml?.green_dot, false),
      detail: ml?.green_dot ? "保護中" : ml?.enabled ? "警示" : "關閉",
    },
    {
      label: "CrimeGuard",
      status: rowStatus(
        !!cg?.enabled,
        !!cg?.green_dot && !cg?.network_locked,
        !!cg?.network_locked || !!cg?.red_dot
      ),
      detail: cg?.network_locked ? "已鎖定" : cg?.vpn_detected ? "VPN" : "正常",
    },
    {
      label: "設備聯繫",
      status: cg?.device_contact_detected ? "warn" : cg?.enabled ? "ok" : "off",
      detail: cg?.device_contact_detected ? cg.device_contact_type || "偵測中" : "無",
    },
    {
      label: "網絡鎖定",
      status: cg?.network_locked ? "locked" : "ok",
      detail: cg?.network_locked ? cg.lock_mode || "active" : "未鎖定",
    },
  ] as const;

  return (
    <div className="px-3 pb-2">
      <button
        type="button"
        onClick={onOpenSecurity}
        className="w-full flex items-center gap-2 px-3 py-2 rounded-xl border border-violet-500/20 bg-gradient-to-r from-violet-500/5 to-blue-500/5 hover:border-blue-500/40 transition-colors text-left"
      >
        <Shield className="w-4 h-4 text-blue-400 shrink-0" />
        <span className="text-sm font-medium text-foreground">安全中心</span>
        <StatusDot
          status={
            cg?.network_locked ? "locked" : cg?.device_contact_detected ? "warn" : "ok"
          }
        />
      </button>
      <div className="mt-2 space-y-1">
        {rows.map((r) => (
          <button
            key={r.label}
            type="button"
            onClick={onOpenSecurity}
            className="w-full flex items-center justify-between px-2 py-1.5 rounded-lg text-xs text-muted-foreground hover:bg-muted/30 hover:text-foreground transition-colors"
          >
            <span className="flex items-center gap-2">
              <StatusDot status={r.status} />
              {r.label}
            </span>
            <span className="truncate max-w-[5rem]">{r.detail}</span>
          </button>
        ))}
      </div>
    </div>
  );
}