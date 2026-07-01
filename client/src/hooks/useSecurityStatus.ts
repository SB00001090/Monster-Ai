import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

export interface RapidCredentialShield {
  rotation_interval?: number;
  token_ttl?: number;
  generation?: number;
  current?: { ttl_seconds?: number; hardware_bound?: boolean };
}

export interface MonsterLockStatus {
  enabled: boolean;
  armed: boolean;
  status: string;
  green_dot: boolean;
  strength: string;
  blocks: number;
  rapid_credential_shield?: RapidCredentialShield;
  events?: Array<{ ts: number; level: string; message: string }>;
}

export interface CrimeGuardStatus {
  enabled: boolean;
  armed: boolean;
  status: string;
  green_dot: boolean;
  red_dot: boolean;
  network_locked: boolean;
  device_locked: boolean;
  device_contact_detected: boolean;
  device_contact_type: string;
  vpn_detected: boolean;
  vpn_type: string;
  lock_mode: string;
  blocks: number;
  locks_triggered: number;
  rules_version: string;
  events?: Array<{ ts: number; level: string; message: string }>;
}

export interface CallGuardStatus {
  enabled: boolean;
  status: string;
  green_dot: boolean;
  red_dot: boolean;
  rejects_today: number;
  reports_today: number;
  threat_db_version: string;
  hk_hotline: string;
  events?: Array<{ ts: number; level: string; message: string }>;
}

export interface SecuritySnapshot {
  monsterlock: MonsterLockStatus;
  crimeguard: CrimeGuardStatus;
  callguard: CallGuardStatus;
}

export interface AppManifest {
  app_version: string;
  apk_url: string;
  apk_filename: string;
  apk_sha256: string;
  releases_page?: string;
  changelog: string;
  threat_db_version: string;
  hk_hotline: string;
  connection_mode?: string;
  qr_code_enabled?: boolean;
  developer?: string;
}

export interface AnonymousReport {
  category: string;
  number_hash: string;
  score: number;
  ts: number;
  signals: string[];
}

export interface PromptAnalysis {
  score: number;
  blocked: boolean;
  lock_trigger: boolean;
  categories: string[];
  matches: string[];
  summary: string;
}

const API_BASE = "";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

function deriveAggregateAlert(cg: CrimeGuardStatus, ml: MonsterLockStatus) {
  if (cg.network_locked || cg.red_dot) return "locked";
  if (cg.device_contact_detected || cg.vpn_detected) return "warn";
  if (ml.green_dot && cg.green_dot) return "ok";
  return "off";
}

export function useSecurityStatus() {
  const [snapshot, setSnapshot] = useState<SecuritySnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [locking, setLocking] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const refresh = useCallback(async () => {
    try {
      const status = await fetchJson<{
        monsterlock: MonsterLockStatus;
        crimeguard: CrimeGuardStatus;
        callguard: CallGuardStatus;
      }>("/api/security/status");
      setSnapshot({
        monsterlock: status.monsterlock,
        crimeguard: status.crimeguard,
        callguard: status.callguard,
      });
    } catch {
      // Python backend may be offline during dev
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const intervalMs = document.hidden ? 10000 : 2500;
    const id = setInterval(() => void refresh(), intervalMs);
    const onVis = () => void refresh();
    document.addEventListener("visibilitychange", onVis);

    try {
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      const ws = new WebSocket(`${proto}//${window.location.host}/api/security/ws/alerts`);
      wsRef.current = ws;
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data as string);
          const msg = data.message || data.summary || "安全警報";
          toast.warning(msg, { duration: 6000 });
          void refresh();
        } catch {
          /* ignore */
        }
      };
      ws.onerror = () => ws.close();
    } catch {
      /* ws optional */
    }

    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", onVis);
      wsRef.current?.close();
    };
  }, [refresh]);

  const triggerLock = useCallback(async (reason = "manual_ui_lock") => {
    setLocking(true);
    try {
      const res = await fetchJson<{ ok: boolean; network_locked: boolean }>(
        "/api/security/crimeguard/lock",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reason }),
        }
      );
      if (res.network_locked) toast.success("網絡已鎖定 — VPN 對策已啟用");
      else toast.error("網絡鎖定失敗");
      await refresh();
      return res.network_locked;
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "鎖定請求失敗");
      return false;
    } finally {
      setLocking(false);
    }
  }, [refresh]);

  const recoverLock = useCallback(async (confirmToken: string) => {
    try {
      await fetchJson("/api/security/crimeguard/recover", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirm_token: confirmToken }),
      });
      toast.success("網絡鎖定已解除");
      await refresh();
      return true;
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "解除失敗 — 請確認 recovery token");
      return false;
    }
  }, [refresh]);

  const analyzePrompt = useCallback(async (message: string): Promise<PromptAnalysis | null> => {
    if (!message.trim()) return null;
    try {
      return await fetchJson<PromptAnalysis>("/api/security/analyze-prompt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, preview_only: true }),
      });
    } catch {
      return null;
    }
  }, []);

  const aggregateStatus = snapshot
    ? deriveAggregateAlert(snapshot.crimeguard, snapshot.monsterlock)
    : "off";

  const threatCount = snapshot ? snapshot.crimeguard.locks_triggered || 0 : 0;

  return {
    snapshot,
    loading,
    locking,
    aggregateStatus,
    threatCount,
    refresh,
    triggerLock,
    recoverLock,
    analyzePrompt,
  };
}