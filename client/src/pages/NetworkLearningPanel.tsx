import { useCallback, useEffect, useState } from "react";
import { NeonPanel, NeonShell } from "@/components/NeonShell";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useBackend } from "@/contexts/BackendContext";
import { getGuardianDisclaimer } from "@/lib/guardianApi";
import { useGuardianNetworkLearning } from "@/hooks/useGuardianNetworkLearning";
import {
  Brain,
  Globe,
  Palette,
  RefreshCw,
  Shield,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";

export default function NetworkLearningPanel() {
  const { online } = useBackend();
  const {
    busy,
    status,
    directives,
    refresh,
    setConsent,
    trigger,
    runArtTriage,
  } = useGuardianNetworkLearning();

  const [disclaimerSnippet, setDisclaimerSnippet] = useState("");
  const [allowMetrics, setAllowMetrics] = useState(false);
  const [forceRun, setForceRun] = useState(false);
  const [customTopics, setCustomTopics] = useState("");

  const load = useCallback(async () => {
    try {
      const [disclaimer] = await Promise.all([
        getGuardianDisclaimer("zh-TW"),
        refresh(),
      ]);
      const text = disclaimer.text ?? "";
      setDisclaimerSnippet(
        text.includes("自主網絡學習")
          ? "§7 自主網絡學習 · 預設關閉 · Grok 審批 · 無私人資料外傳"
          : "Monster Guardian AI",
      );
    } catch {
      setDisclaimerSnippet("Guardian API 離線");
    }
  }, [refresh]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleConsent = async (consented: boolean) => {
    try {
      await setConsent(consented, allowMetrics);
      toast.success(consented ? "已授予網絡學習同意" : "已撤銷網絡學習同意");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "同意設定失敗");
    }
  };

  const handleTrigger = async () => {
    try {
      const topics = customTopics
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      const result = await trigger({
        force: forceRun,
        topics: topics.length > 0 ? topics : undefined,
      });
      if (result.ok) {
        toast.success("網絡學習執行完成");
      } else {
        const reason = String((result as { reason?: string }).reason ?? "unknown");
        toast.error(`學習未執行：${reason}`);
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "觸發失敗");
    }
  };

  const handleArtTriage = async () => {
    try {
      const result = await runArtTriage();
      if (result.ok) {
        const counts = (result as { counts?: Record<string, number> }).counts;
        toast.success(
          `藝術分類完成 · real ${counts?.real ?? 0} · good ${counts?.good ?? 0}`,
        );
      } else {
        toast.error(String((result as { reason?: string }).reason ?? "art_triage_failed"));
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "藝術分類失敗");
    }
  };

  const schedule = status?.schedule;
  const artTriage = (status?.art_triage ?? {}) as Record<string, unknown>;
  const counts = (artTriage.counts ?? {}) as Record<string, number>;

  return (
    <NeonShell
      title="自主網絡學習"
      subtitle="Opt-in · Grok 監督 · 隱私防火牆 · 藝術分類強化"
      badge="Developed by Suckbob | Monster Guardian AI"
    >
      <div className="grid lg:grid-cols-2 gap-4">
        <NeonPanel className="space-y-4">
          <h2 className="font-semibold text-[var(--neon-cyan)] flex items-center gap-2">
            <Shield className="w-4 h-4" /> 狀態與免責
          </h2>
          <div className="flex flex-wrap gap-2 text-xs">
            <Badge variant={status?.enabled ? "default" : "secondary"}>
              模組 {status?.enabled ? "已啟用" : "關閉"}
            </Badge>
            <Badge variant={status?.user_consented ? "default" : "destructive"}>
              同意 {status?.user_consented ? "已授予" : "未授予"}
            </Badge>
            <Badge variant={online ? "default" : "secondary"}>
              API {online ? "連線" : "離線"}
            </Badge>
            {status?.require_grok_approval && (
              <Badge variant="outline">Grok 審批</Badge>
            )}
          </div>
          <p className="text-xs text-[var(--neon-muted)]">{disclaimerSnippet}</p>
          {schedule && (
            <p className="text-xs text-[var(--neon-muted)]">
              排程 {schedule.windows?.join(", ") ?? "—"} ·{" "}
              {schedule.in_window ? "目前在視窗內" : "視窗外"}
            </p>
          )}
          {status?.last_run_at && (
            <p className="text-xs font-mono text-[var(--neon-muted)]">
              上次執行：{new Date(status.last_run_at * 1000).toLocaleString()} ·{" "}
              {status.last_run_ok ? "成功" : "失敗/部分"}
            </p>
          )}
        </NeonPanel>

        <NeonPanel className="space-y-4">
          <h2 className="font-semibold text-[var(--neon-cyan)] flex items-center gap-2">
            <Globe className="w-4 h-4" /> 同意管理
          </h2>
          <p className="text-xs text-[var(--neon-muted)]">
            預設關閉。授予同意後，系統才會在排程視窗連接公開來源學習；OC／聊天／vault 明文永不外傳。
          </p>
          <label className="flex items-center gap-2 text-xs cursor-pointer">
            <Checkbox
              checked={allowMetrics}
              onCheckedChange={(c) => setAllowMetrics(c === true)}
            />
            允許匿名聚合指標（不含私人內容）
          </label>
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              className="neon-btn-primary"
              disabled={busy || !online}
              onClick={() => void handleConsent(true)}
            >
              授予同意
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={busy}
              onClick={() => void handleConsent(false)}
            >
              撤銷同意
            </Button>
            <Button
              size="sm"
              variant="ghost"
              disabled={busy}
              onClick={() => void load()}
            >
              <RefreshCw className={`w-3 h-3 ${busy ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </NeonPanel>

        <NeonPanel className="space-y-4 lg:col-span-2">
          <h2 className="font-semibold text-[var(--neon-cyan)] flex items-center gap-2">
            <Brain className="w-4 h-4" /> 手動觸發學習
          </h2>
          <div className="grid sm:grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">自訂主題（逗號分隔，可留空）</Label>
              <Input
                value={customTopics}
                onChange={(e) => setCustomTopics(e.target.value)}
                placeholder="AI 技術新聞, diffusion research"
              />
            </div>
            <label className="flex items-center gap-2 text-xs pt-6 cursor-pointer">
              <Checkbox
                checked={forceRun}
                onCheckedChange={(c) => setForceRun(c === true)}
              />
              強制執行（跳過排程視窗）
            </label>
          </div>
          <Button
            className="neon-btn-primary gap-2"
            disabled={busy || !status?.user_consented || online === false}
            onClick={() => void handleTrigger()}
          >
            {busy ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            觸發網絡學習
          </Button>
        </NeonPanel>

        {status?.art_triage_enabled && (
          <NeonPanel className="space-y-4">
            <h2 className="font-semibold text-[var(--neon-cyan)] flex items-center gap-2">
              <Palette className="w-4 h-4" /> 藝術分類（G5b）
            </h2>
            <p className="text-xs text-[var(--neon-muted)]">
              好圖 / 爛圖 / 參考級 — 僅更新加密 vault metadata
            </p>
            <div className="flex gap-2 text-xs font-mono">
              <span>real {counts.real ?? 0}</span>
              <span>good {counts.good ?? 0}</span>
              <span>bad {counts.bad ?? 0}</span>
              <span>patched {counts.patched ?? 0}</span>
            </div>
            <Button
              size="sm"
              variant="outline"
              disabled={busy}
              onClick={() => void handleArtTriage()}
            >
              執行藝術分類
            </Button>
          </NeonPanel>
        )}

        <NeonPanel className="space-y-3 lg:col-span-2">
          <h2 className="font-semibold text-[var(--neon-cyan)] text-sm">
            Grok 學習指令
          </h2>
          {directives.length === 0 ? (
            <p className="text-xs text-muted-foreground">尚無指令記錄</p>
          ) : (
            <ul className="text-xs space-y-2">
              {directives.map((d, i) => (
                <li
                  key={`dir-${i}`}
                  className="p-2 rounded border border-border/50 font-mono"
                >
                  <span className="text-[var(--neon-cyan)]">
                    {d.approved === false ? "denied" : "ok"}
                  </span>{" "}
                  {String(d.reason ?? d.reviewed_at ?? JSON.stringify(d).slice(0, 120))}
                </li>
              ))}
            </ul>
          )}
        </NeonPanel>
      </div>
    </NeonShell>
  );
}