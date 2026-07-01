import { useCallback, useState } from "react";
import {
  getNetworkLearningDirectives,
  getNetworkLearningStatus,
  postArtTriageRun,
  getArtTriageStatus,
  postNetworkLearningConsent,
  postNetworkLearningTrigger,
} from "@/lib/guardianApi";

export type NetworkLearningStatus = {
  enabled?: boolean;
  user_consented?: boolean;
  consented_at?: number;
  require_grok_approval?: boolean;
  art_triage_enabled?: boolean;
  schedule?: { in_window?: boolean; windows?: string[]; next_window_hint?: string };
  last_run_at?: number;
  last_run_ok?: boolean;
  art_triage?: Record<string, unknown>;
};

export function useGuardianNetworkLearning() {
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<NetworkLearningStatus | null>(null);
  const [directives, setDirectives] = useState<Array<Record<string, unknown>>>([]);

  const refresh = useCallback(async () => {
    const [st, dirs] = await Promise.all([
      getNetworkLearningStatus(),
      getNetworkLearningDirectives(8),
    ]);
    setStatus(st as NetworkLearningStatus);
    setDirectives(dirs.directives ?? []);
    return st;
  }, []);

  const setConsent = useCallback(
    async (consented: boolean, metrics = false) => {
      setBusy(true);
      try {
        const result = await postNetworkLearningConsent(consented, metrics);
        await refresh();
        return result;
      } finally {
        setBusy(false);
      }
    },
    [refresh],
  );

  const trigger = useCallback(
    async (opts?: { force?: boolean; topics?: string[] }) => {
      setBusy(true);
      try {
        const result = await postNetworkLearningTrigger({
          force: opts?.force ?? false,
          topics: opts?.topics,
        });
        await refresh();
        return result;
      } finally {
        setBusy(false);
      }
    },
    [refresh],
  );

  const runArtTriage = useCallback(async () => {
    setBusy(true);
    try {
      const result = await postArtTriageRun();
      await refresh();
      return result;
    } finally {
      setBusy(false);
    }
  }, [refresh]);

  const fetchArtTriageStatus = useCallback(async () => {
    return getArtTriageStatus();
  }, []);

  return {
    busy,
    status,
    directives,
    refresh,
    setConsent,
    trigger,
    runArtTriage,
    fetchArtTriageStatus,
  };
}