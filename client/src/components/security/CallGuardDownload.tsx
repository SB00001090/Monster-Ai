import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Download, ChevronDown, ChevronUp, Smartphone, Wifi, ExternalLink } from "lucide-react";
import type { AppManifest } from "@/hooks/useSecurityStatus";

const DEFAULT_GITHUB_RELEASES =
  "https://github.com/SB00001090/Monster-Ai/releases/latest";

interface Props {
  manifest: AppManifest | null;
  compact?: boolean;
}

export default function CallGuardDownload({ manifest, compact = false }: Props) {
  const [expanded, setExpanded] = useState(!compact);
  const [homeUrl, setHomeUrl] = useState("");
  const [connStatus, setConnStatus] = useState<"idle" | "ok" | "fail">("idle");

  const version = manifest?.app_version || "1.2.0";
  const apkUrl =
    manifest?.apk_url ||
    `https://github.com/SB00001090/Monster-Ai/releases/download/v${version}/MonsterCallGuard-v${version}-signed.apk`;
  const releasesUrl = manifest?.releases_page || DEFAULT_GITHUB_RELEASES;
  const sha = manifest?.apk_sha256 || "";
  const shaShort = sha ? `${sha.slice(0, 16)}…` : "—";

  const testConnection = async () => {
    const base = homeUrl.trim().replace(/\/$/, "");
    if (!base) return;
    setConnStatus("idle");
    try {
      const res = await fetch(`${base}/health`);
      setConnStatus(res.ok ? "ok" : "fail");
    } catch {
      setConnStatus("fail");
    }
  };

  if (compact) {
    return (
      <div className="px-3 pb-2">
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="w-full flex items-center justify-between px-3 py-2 rounded-xl border border-border/50 bg-muted/20 text-sm"
        >
          <span className="flex items-center gap-2">
            <Smartphone className="w-4 h-4 text-blue-400" />
            CallGuard v{version}
          </span>
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        {expanded && (
          <div className="mt-2">
            <CallGuardDownload manifest={manifest} />
          </div>
        )}
      </div>
    );
  }

  return (
    <Card className="p-5 bg-card/60 border border-violet-500/20 shadow-[0_0_20px_rgba(59,130,246,0.08)]">
      <div className="flex flex-col gap-4">
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <Smartphone className="w-5 h-5 text-blue-400" />
            MonsterCallGuard
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            Developed by Suckbob | Monster AI Call Guard
          </p>
          <p className="text-sm text-muted-foreground mt-1">
            香港來電反制 · 收數公司自動拒接 · 設備聯繫即時網絡鎖定
          </p>
          <p className="text-xs text-muted-foreground mt-2">
            v{version} · 已簽署 APK · GitHub Releases 分發
          </p>
          <p className="text-xs font-mono text-muted-foreground mt-1 break-all">
            SHA256: {shaShort}
          </p>
          {manifest?.changelog && (
            <p className="text-xs text-muted-foreground mt-2">{manifest.changelog}</p>
          )}
          <div className="flex flex-wrap gap-2 mt-4">
            <Button asChild className="rounded-full gap-2">
              <a href={apkUrl} download rel="noopener noreferrer">
                <Download className="w-4 h-4" />
                下載 APK
              </a>
            </Button>
            <Button asChild variant="outline" className="rounded-full gap-2">
              <a href={releasesUrl} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="w-4 h-4" />
                GitHub Releases
              </a>
            </Button>
          </div>

          <details className="mt-4 text-sm">
            <summary className="cursor-pointer text-blue-400 hover:underline">
              側載安裝與安全說明
            </summary>
            <ol className="mt-2 space-y-1 text-muted-foreground text-xs list-decimal list-inside">
              <li>從 GitHub Releases 下載 APK，比對 SHA256</li>
              <li>設定 → 安全性 → 允許安裝未知應用程式</li>
              <li>授予電話、通話紀錄、通知權限</li>
              <li>設為預設「來電篩選」App（Android 10+）</li>
              <li>手動貼上 Cloudflare Tunnel URL（唔使 IP、唔掃 QR）</li>
              <li>無廣告、無通話錄音；舉報僅上傳號碼 hash</li>
            </ol>
          </details>

          <details className="mt-3 text-sm" open>
            <summary className="cursor-pointer text-blue-400 hover:underline flex items-center gap-1">
              <Wifi className="w-3 h-3" />
              Cloudflare Tunnel 連線
            </summary>
            <div className="mt-2 space-y-2 text-xs">
              <p className="text-muted-foreground">
                電腦執行 <code className="text-foreground">run-tunnel.bat</code>，手動貼上 HTTPS URL
              </p>
              <p className="text-muted-foreground">
                例：<code className="text-foreground">https://xxx.trycloudflare.com</code>
              </p>
              <div className="flex gap-2">
                <input
                  type="url"
                  value={homeUrl}
                  onChange={(e) => setHomeUrl(e.target.value)}
                  placeholder="https://xxx.trycloudflare.com"
                  className="flex-1 rounded-lg bg-muted/40 border border-border/50 px-2 py-1.5 text-foreground"
                />
                <Button size="sm" variant="outline" onClick={() => void testConnection()}>
                  測試
                </Button>
              </div>
              {connStatus === "ok" && (
                <span className="text-emerald-400">Tunnel 連線成功</span>
              )}
              {connStatus === "fail" && (
                <span className="text-red-400">連線失敗 — 確認 main.py + cloudflared 運行中</span>
              )}
            </div>
          </details>
        </div>
      </div>
    </Card>
  );
}