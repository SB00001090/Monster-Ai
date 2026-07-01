import { useState } from "react";
import { NeonPanel, NeonShell } from "@/components/NeonShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useBackend } from "@/contexts/BackendContext";
import {
  getGenProvider,
  setGenProvider,
  type GenProvider,
} from "@/lib/integrations";
import { monsterWsUrl } from "@/lib/monsterApi";
import { Cloud, Globe, Link2, Server, Workflow } from "lucide-react";
import { toast } from "sonner";

export default function DeployPage() {
  const { apiBase, setApiBase, online, version, refresh } = useBackend();
  const [draft, setDraft] = useState(apiBase);
  const [provider, setProvider] = useState<GenProvider>(getGenProvider);

  const save = () => {
    setApiBase(draft);
    void refresh();
    toast.success("Tunnel URL 已儲存");
  };

  const switchProvider = (p: GenProvider) => {
    setGenProvider(p);
    setProvider(p);
    toast.success(p === "dify" ? "Dify 工作流模式" : "Monster 原生模式");
  };

  const ws = typeof window !== "undefined" ? monsterWsUrl() : "";

  return (
    <NeonShell
      title="部署與連線"
      subtitle="Cloudflare Pages 前端 + Cloudflare Tunnel 暴露本機 Monster AI 後端"
      badge="Developed by Suckbob | Monster AI"
    >
      <div className="grid md:grid-cols-2 gap-4">
        <NeonPanel className="space-y-4">
          <h2 className="font-semibold text-[var(--neon-cyan)] flex items-center gap-2">
            <Link2 className="w-4 h-4" /> 後端 API URL
          </h2>
          <p className="text-xs text-[var(--neon-muted)]">
            本機開發留空（同源代理）。Pages 部署後填入 Tunnel 網址，或設 Pages Secret
            VITE_MONSTER_API_URL
          </p>
          <div>
            <Label className="text-xs">Tunnel URL</Label>
            <Input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="https://your-tunnel.trycloudflare.com"
            />
          </div>
          <Button className="neon-btn-primary" onClick={save}>
            儲存並測試連線
          </Button>
          <div className="text-sm">
            狀態:{" "}
            <span className={online ? "text-[var(--neon-green)]" : "text-[var(--neon-pink)]"}>
              {online === null ? "檢測中…" : online ? `線上 v${version}` : "離線"}
            </span>
          </div>
          <div className="text-xs text-[var(--neon-muted)] break-all">
            WebSocket: {ws || "（Pages 需設定 Tunnel URL）"}
          </div>
        </NeonPanel>

        <NeonPanel className="space-y-4">
          <h2 className="font-semibold text-[var(--neon-cyan)] flex items-center gap-2">
            <Workflow className="w-4 h-4" /> 生成 Provider
          </h2>
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant={provider === "monster" ? "default" : "outline"}
              className={provider === "monster" ? "neon-btn-primary" : ""}
              onClick={() => switchProvider("monster")}
            >
              Monster 原生
            </Button>
            <Button
              size="sm"
              variant={provider === "dify" ? "default" : "outline"}
              className={provider === "dify" ? "neon-btn-primary" : ""}
              onClick={() => switchProvider("dify")}
            >
              Dify 並行
            </Button>
          </div>
          <p className="text-xs text-[var(--neon-muted)]">
            Dify 未設定時自動 fallback 至 Monster。詳見「平台整合」頁。
          </p>
          <Button size="sm" variant="outline" asChild>
            <a href="/integrations">開啟平台整合</a>
          </Button>
        </NeonPanel>

        <NeonPanel className="space-y-3 text-sm text-[var(--neon-muted)] md:col-span-2">
          <h2 className="font-semibold text-[var(--neon-cyan)] flex items-center gap-2">
            <Cloud className="w-4 h-4" /> 快速上架（免費）
          </h2>
          <ol className="list-decimal list-inside space-y-2">
            <li>
              <Globe className="inline w-3 h-3 mr-1" />
              推送 Git → Cloudflare Pages 自動建置（見 deploy/cloudflare/）
            </li>
            <li>
              <Server className="inline w-3 h-3 mr-1" />
              本機執行 <code className="text-[var(--neon-cyan)]">scripts/deploy_cloudflare.py --tunnel</code>
            </li>
            <li>將 Tunnel URL 貼到上方（或設 Pages 環境變數 VITE_MONSTER_API_URL）</li>
            <li>本機 python main.py + Ollama + ComfyUI 持續運行</li>
            <li>可選：Make 自動化（deploy/make/SCENARIO.md）、Sentry、Jam、HF Space</li>
          </ol>
          <p className="text-[10px] border-t border-[var(--neon-border)] pt-3">
            核心運算留在本機。Tunnel 僅加密轉發 API。R18+ 內容責任由用戶自負，須年滿 18 歲。
          </p>
        </NeonPanel>
      </div>
    </NeonShell>
  );
}