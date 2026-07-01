import { useCallback, useEffect, useState } from "react";
import { NeonPanel, NeonShell } from "@/components/NeonShell";
import { Button } from "@/components/ui/button";
import { useBackend } from "@/contexts/BackendContext";
import { monsterApi, type EcosystemBundle } from "@/lib/monsterApi";
import { toast } from "sonner";
import { Download, Shield, Zap } from "lucide-react";

export default function EcosystemPage() {
  const { online } = useBackend();
  const [bundles, setBundles] = useState<EcosystemBundle[]>([]);
  const [selected, setSelected] = useState("full");
  const [privacy, setPrivacy] = useState("");
  const [consented, setConsented] = useState(false);
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const info = await monsterApi.ecosystemInfo();
      setBundles(info.bundles || []);
      setConsented(Boolean((info.consent as { consented?: boolean })?.consented));
      setStatus((info.status as Record<string, unknown>) || null);
    } catch (e) {
      toast.error(String(e));
    }
  }, []);

  useEffect(() => {
    load();
    monsterApi.ecosystemPrivacy("zh-TW").then((d) => setPrivacy(d.text)).catch(() => {});
    const id = setInterval(async () => {
      try {
        setStatus(await monsterApi.ecosystemStatus());
      } catch {
        /* ignore */
      }
    }, 3000);
    return () => clearInterval(id);
  }, [load]);

  const grant = async () => {
    setBusy(true);
    try {
      await monsterApi.ecosystemConsent({
        grant: true,
        allow_r18: true,
        allow_downloads: true,
      });
      setConsented(true);
      toast.success("已同意網絡安裝條款");
    } catch (e) {
      toast.error(String(e));
    } finally {
      setBusy(false);
    }
  };

  const install = async () => {
    if (!consented) {
      toast.error("請先同意隱私與免責條款");
      return;
    }
    setBusy(true);
    try {
      await monsterApi.ecosystemInstall(selected);
      toast.success(`已開始安裝：${selected}`);
      load();
    } catch (e) {
      toast.error(String(e));
    } finally {
      setBusy(false);
    }
  };

  const pct = Number(status?.progress_pct ?? 0);

  return (
    <NeonShell
      title="一鍵安裝完整生態"
      subtitle="RP + 圖像 + 影片 + 音訊 + R18+ + Likeness · 安全網絡下載 · 與 Mini 雙向共享"
      badge="Developed by Suckbob | Monster AI"
    >
      {!online && (
        <NeonPanel className="border-[var(--neon-pink)]">
          <p className="text-sm text-[var(--neon-pink)]">
            後端離線 — 請在「部署連線」設定 Tunnel URL，或本機執行 python main.py
          </p>
        </NeonPanel>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        <NeonPanel>
          <h2 className="text-[var(--neon-cyan)] font-semibold mb-3 flex items-center gap-2">
            <Zap className="w-4 h-4" /> 安裝包
          </h2>
          <div className="grid gap-2">
            {bundles.map((b) => (
              <button
                key={b.id}
                type="button"
                onClick={() => setSelected(b.id)}
                className={`text-left rounded-lg border px-3 py-2 transition ${
                  selected === b.id
                    ? "border-[var(--neon-cyan)] bg-[var(--neon-cyan)]/10"
                    : "border-[var(--neon-border)] hover:border-[var(--neon-cyan)]/50"
                }`}
              >
                <div className="font-medium text-sm">{b.label || b.id}</div>
                <div className="text-xs text-[var(--neon-muted)]">
                  ~{b.estimated_minutes ?? "?"} 分 · {b.step_count ?? 0} 步驟
                </div>
              </button>
            ))}
          </div>
          <Button
            className="w-full mt-4 neon-btn-primary"
            disabled={busy || !online}
            onClick={install}
          >
            <Download className="w-4 h-4 mr-2" />
            一鍵安裝完整生態
          </Button>
        </NeonPanel>

        <NeonPanel>
          <h2 className="text-[var(--neon-cyan)] font-semibold mb-3 flex items-center gap-2">
            <Shield className="w-4 h-4" /> 隱私與進度
          </h2>
          <pre className="text-xs text-[var(--neon-muted)] whitespace-pre-wrap max-h-40 overflow-auto mb-3">
            {privacy || "載入免責聲明…"}
          </pre>
          {!consented ? (
            <Button variant="outline" className="w-full mb-3" disabled={busy} onClick={grant}>
              同意並啟用網絡下載
            </Button>
          ) : (
            <p className="text-xs text-[var(--neon-green)] mb-3">✓ 已同意網絡安裝</p>
          )}
          <div className="h-2 rounded-full bg-black/40 overflow-hidden mb-2">
            <div
              className="h-full bg-gradient-to-r from-[var(--neon-cyan)] to-[var(--neon-pink)] transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
          <p className="text-xs text-[var(--neon-muted)]">
            {status?.running
              ? `執行中: ${String(status.current_step || "…")} (${pct.toFixed(1)}%)`
              : status?.bundle_id
                ? `完成: ${String(status.bundle_id)}`
                : "待機"}
          </p>
        </NeonPanel>
      </div>
    </NeonShell>
  );
}