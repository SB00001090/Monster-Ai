import { useCallback, useEffect, useState } from "react";
import { NeonPanel, NeonShell } from "@/components/NeonShell";
import { QualityRing } from "@/components/QualityRing";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useBackend } from "@/contexts/BackendContext";
import { monsterApi } from "@/lib/monsterApi";
import {
  getDifyConfig,
  getGenProvider,
  setDifyConfig,
  setGenProvider,
  type GenProvider,
} from "@/lib/integrations";
import {
  Activity,
  Cloud,
  ExternalLink,
  GitBranch,
  Layers,
  Shield,
  Video,
  Workflow,
} from "lucide-react";
import { toast } from "sonner";

type Status = Record<string, unknown>;

const HF_SPACE = "https://huggingface.co/spaces/SB00001090/monster-ai-demo";

function StatusDot({ ok }: { ok?: boolean | null }) {
  const color =
    ok === null || ok === undefined
      ? "bg-[var(--neon-muted)]"
      : ok
        ? "bg-[var(--neon-green)]"
        : "bg-[var(--neon-pink)]";
  return <span className={`inline-block w-2 h-2 rounded-full ${color}`} />;
}

export default function IntegrationsPage() {
  const { online } = useBackend();
  const [status, setStatus] = useState<Status | null>(null);
  const [provider, setProvider] = useState<GenProvider>(getGenProvider);
  const [difyUrl, setDifyUrl] = useState("");
  const [difyKey, setDifyKey] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const s = await monsterApi.integrationsStatus();
      setStatus(s);
    } catch {
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    const cfg = getDifyConfig();
    setDifyUrl(cfg.url);
    setDifyKey(cfg.apiKey);
    void refresh();
  }, [refresh]);

  const saveDify = () => {
    setDifyConfig(difyUrl, difyKey);
    toast.success("Dify 設定已儲存（本機）");
  };

  const saveProvider = (p: GenProvider) => {
    setGenProvider(p);
    setProvider(p);
    toast.success(p === "dify" ? "已切換至 Dify 工作流" : "已切換至 Monster 原生");
  };

  const testDify = async () => {
    setBusy(true);
    try {
      const r = await monsterApi.difyStatus();
      toast.success(r.configured ? "Dify 已連線" : "Dify 未設定 — 將使用 Monster 後備");
      void refresh();
    } catch (e) {
      toast.error(String(e));
    } finally {
      setBusy(false);
    }
  };

  const dify = (status?.dify as Record<string, unknown>) || {};
  const mini = (status?.mini_success as Record<string, unknown>) || {};
  const curriculum = (status?.curriculum as Record<string, unknown>) || {};
  const successRate = Number(mini.success_rate ?? 0);
  const threshold = Number(status?.quality_threshold ?? 0.7);

  return (
    <NeonShell
      title="平台整合"
      subtitle="Dify · Hugging Face · Make · Sentry · Jam · Cloudflare — 一頁總覽"
      badge={online ? "後端連線中" : "後端離線"}
    >
      <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
        <NeonPanel className="space-y-3">
          <h2 className="font-semibold text-[var(--neon-cyan)] flex items-center gap-2">
            <Workflow className="w-4 h-4" /> 生成引擎
          </h2>
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant={provider === "monster" ? "default" : "outline"}
              className={provider === "monster" ? "neon-btn-primary" : ""}
              onClick={() => saveProvider("monster")}
            >
              Monster 原生
            </Button>
            <Button
              size="sm"
              variant={provider === "dify" ? "default" : "outline"}
              className={provider === "dify" ? "neon-btn-primary" : ""}
              onClick={() => saveProvider("dify")}
            >
              Dify 工作流
            </Button>
          </div>
          <p className="text-xs text-[var(--neon-muted)]">
            品質閾值 <strong className="text-[var(--neon-cyan)]">70%</strong> — 低於自動重試並進入學習迴圈
          </p>
          <div className="flex items-center gap-4">
            <QualityRing score={successRate} label="Mini 成功率" />
            <QualityRing score={threshold} passed label="品質門檻" />
          </div>
        </NeonPanel>

        <NeonPanel className="space-y-3">
          <h2 className="font-semibold text-[var(--neon-cyan)] flex items-center gap-2">
            <Layers className="w-4 h-4" /> Dify
            <StatusDot ok={Boolean(dify.configured)} />
          </h2>
          <div>
            <Label className="text-xs">API URL（選填，後端 config.yaml 優先）</Label>
            <Input value={difyUrl} onChange={(e) => setDifyUrl(e.target.value)} placeholder="https://api.dify.ai/v1" />
          </div>
          <div>
            <Label className="text-xs">API Key（本機儲存）</Label>
            <Input type="password" value={difyKey} onChange={(e) => setDifyKey(e.target.value)} />
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={saveDify}>
              儲存
            </Button>
            <Button size="sm" className="neon-btn-primary" disabled={busy} onClick={testDify}>
              測試連線
            </Button>
          </div>
          <p className="text-[10px] text-[var(--neon-muted)]">
            匯入 <code>deploy/dify/workflow_image_quality.json</code> 至 Dify Studio
          </p>
        </NeonPanel>

        <NeonPanel className="space-y-3">
          <h2 className="font-semibold text-[var(--neon-cyan)] flex items-center gap-2">
            <Cloud className="w-4 h-4" /> Cloudflare
            <StatusDot ok={online} />
          </h2>
          <ul className="text-sm space-y-2 text-[var(--neon-muted)]">
            <li>
              Pages:{" "}
              <a
                href="https://monster-ai.pages.dev"
                target="_blank"
                rel="noreferrer"
                className="text-[var(--neon-cyan)] hover:underline inline-flex items-center gap-1"
              >
                monster-ai.pages.dev <ExternalLink className="w-3 h-3" />
              </a>
            </li>
            <li>Tunnel → 本機 :7860（見「部署連線」頁）</li>
          </ul>
          <Button size="sm" variant="outline" asChild>
            <a href="/deploy">開啟部署設定</a>
          </Button>
        </NeonPanel>

        <NeonPanel className="space-y-3">
          <h2 className="font-semibold text-[var(--neon-cyan)] flex items-center gap-2">
            <GitBranch className="w-4 h-4" /> Hugging Face
          </h2>
          <p className="text-xs text-[var(--neon-muted)]">
            Spaces 公開 Demo + Inference Endpoint 託管模型
          </p>
          <Button size="sm" variant="outline" asChild>
            <a href={HF_SPACE} target="_blank" rel="noreferrer">
              開啟 HF Space <ExternalLink className="w-3 h-3 ml-1" />
            </a>
          </Button>
          <p className="text-[10px] text-[var(--neon-muted)]">設定見 deploy/huggingface/</p>
        </NeonPanel>

        <NeonPanel className="space-y-3">
          <h2 className="font-semibold text-[var(--neon-cyan)] flex items-center gap-2">
            <Activity className="w-4 h-4" /> Make 自動化
            <StatusDot ok={Boolean(status?.make_secret_configured)} />
          </h2>
          <p className="text-xs text-[var(--neon-muted)]">
            Git push → Cloudflare Pages 建置 · 失敗通知 · 數據同步
          </p>
          <p className="text-[10px] font-mono break-all">
            POST /api/integrations/make/deploy-hook
          </p>
          <p className="text-[10px] text-[var(--neon-muted)]">
            情境設定見 repo deploy/make/SCENARIO.md
          </p>
        </NeonPanel>

        <NeonPanel className="space-y-3">
          <h2 className="font-semibold text-[var(--neon-cyan)] flex items-center gap-2">
            <Shield className="w-4 h-4" /> Sentry + Jam
          </h2>
          <ul className="text-sm space-y-1 text-[var(--neon-muted)]">
            <li className="flex items-center gap-2">
              <StatusDot ok={Boolean(status?.sentry_configured)} /> Sentry DSN
            </li>
            <li className="flex items-center gap-2">
              <StatusDot ok={Boolean(import.meta.env.VITE_JAM_TEAM_ID)} /> Jam 錄影回報
            </li>
          </ul>
          <p className="text-[10px] text-[var(--neon-muted)]">
            設定 SENTRY_DSN、VITE_SENTRY_DSN、VITE_JAM_TEAM_ID 於 .env
          </p>
          <p className="text-[10px] text-[var(--neon-muted)]">
            Wix Landing 結構見 deploy/wix/LANDING.md
          </p>
        </NeonPanel>

        <NeonPanel className="space-y-3 md:col-span-2 xl:col-span-3">
          <h2 className="font-semibold text-[var(--neon-cyan)] flex items-center gap-2">
            <Video className="w-4 h-4" /> 學習迴圈狀態
          </h2>
          <div className="grid sm:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-[var(--neon-muted)]">課程進度</span>
              <p className="font-mono text-[var(--neon-cyan)]">
                {curriculum.completed_topics != null
                  ? `${curriculum.completed_topics}/${curriculum.total_topics ?? "?"} 主題`
                  : "—"}
              </p>
            </div>
            <div>
              <span className="text-[var(--neon-muted)]">預估剩餘</span>
              <p className="font-mono text-[var(--neon-cyan)]">
                {curriculum.eta_hours != null
                  ? `${Number(curriculum.eta_hours).toFixed(1)}h`
                  : "—"}
              </p>
            </div>
            <div>
              <span className="text-[var(--neon-muted)]">Mini 記錄</span>
              <p className="font-mono text-[var(--neon-cyan)]">
                {mini.total_recorded != null ? String(mini.total_recorded) : "—"} 次
              </p>
            </div>
          </div>
        </NeonPanel>
      </div>
    </NeonShell>
  );
}