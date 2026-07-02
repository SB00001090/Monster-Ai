import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/_core/hooks/useAuth";
import { useGuest } from "@/contexts/GuestContext";
import { NeonPanel, NeonShell } from "@/components/NeonShell";
import OAuthProviderButtons from "@/components/OAuthProviderButtons";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useBackend } from "@/contexts/BackendContext";
import {
  getGuardianConnection,
  getGuardianDisclaimer,
  getGuardianStatus,
  type SyncBundleType,
} from "@/lib/guardianApi";
import { resolveOAuthProvider } from "@/lib/guardianOAuth";
import { useGuardianSync, type MergeStrategy } from "@/hooks/useGuardianSync";
import {
  Cloud,
  CloudDownload,
  CloudUpload,
  Lock,
  RefreshCw,
  Shield,
} from "lucide-react";
import { toast } from "sonner";

const BUNDLE_OPTIONS: { id: SyncBundleType; label: string; hint: string }[] = [
  { id: "oc_cards", label: "OC 角色卡", hint: "角色文案與設定" },
  { id: "chat_sessions", label: "聊天對話", hint: "對話記錄" },
  { id: "preferences", label: "偏好設定", hint: "主題、Tunnel URL 等" },
  {
    id: "training_vault",
    label: "訓練 Vault",
    hint: "已加密的好圖/爛圖/模板（密文上傳）",
  },
];

export default function GuardianSyncPage() {
  const { user } = useAuth();
  const { isGuest } = useGuest();
  const { online } = useBackend();
  const {
    busy,
    bundles,
    lastSync,
    refreshManifest,
    uploadAll,
    downloadBundle,
    applyDownloaded,
  } = useGuardianSync();

  const [passphrase, setPassphrase] = useState("");
  const [selected, setSelected] = useState<Set<SyncBundleType>>(
    () => new Set(["oc_cards", "chat_sessions"]),
  );
  const [mergeStrategy, setMergeStrategy] = useState<MergeStrategy>("merge");
  const [guardianOk, setGuardianOk] = useState<boolean | null>(null);
  const [tunnelUrl, setTunnelUrl] = useState<string | null>(null);
  const [disclaimerLine, setDisclaimerLine] = useState("");
  const [desktopVault, setDesktopVault] = useState<string | null>(null);

  const provider = useMemo(
    () => resolveOAuthProvider(user?.loginMethod),
    [user?.loginMethod],
  );
  const providerSub = user?.openId ?? "";

  const canSync =
    !isGuest &&
    Boolean(user) &&
    Boolean(provider) &&
    Boolean(providerSub) &&
    passphrase.length >= 8 &&
    online !== false;

  const toggleBundle = (id: SyncBundleType, checked: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const loadMeta = useCallback(async () => {
    try {
      const [status, conn, disclaimer] = await Promise.all([
        getGuardianStatus(),
        getGuardianConnection(),
        getGuardianDisclaimer("zh-TW"),
      ]);
      setGuardianOk(Boolean(status.enabled && status.healthy));
      setTunnelUrl((conn.tunnel_url as string) ?? null);
      const text = disclaimer.text ?? "";
      setDisclaimerLine(
        text.includes("不接受退款") || text.includes("No refunds")
          ? "免責聲明已載入 · 端到端加密 · 不接受退款"
          : "免責聲明已載入 · 端到端加密",
      );
    } catch {
      setGuardianOk(false);
    }
  }, []);

  useEffect(() => {
    void loadMeta();
    if (typeof window !== "undefined" && window.electron?.guardianVaultStatus) {
      void window.electron.guardianVaultStatus().then((s) => {
        if (s.configured) {
          setDesktopVault(
            s.fingerprint
              ? `Electron 金鑰已設定 · fp ${s.fingerprint.slice(0, 8)}…`
              : "Electron 金鑰已設定",
          );
        }
      });
    }
  }, [loadMeta]);

  useEffect(() => {
    if (provider && providerSub && passphrase.length >= 8) {
      void refreshManifest(provider, providerSub).catch(() => {
        /* backend offline */
      });
    }
  }, [provider, providerSub, passphrase, refreshManifest]);

  const handleUpload = async () => {
    if (!canSync || !provider) return;
    try {
      const types = [...selected];
      if (types.length === 0) {
        toast.error("請至少選擇一項同步內容");
        return;
      }
      await uploadAll({
        provider,
        providerSub,
        passphrase,
        types,
      });
      toast.success(`已加密上傳 ${types.length} 項 bundle`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "上傳失敗");
    }
  };

  const handleDownloadApply = async (bundleType: SyncBundleType) => {
    if (!canSync || !provider) return;
    try {
      const result = await downloadBundle({
        provider,
        providerSub,
        passphrase,
        bundleType,
      });
      if (!result.ok) {
        const reason = (result as { reason?: string }).reason ?? "unknown";
        toast.error(
          reason === "decrypt_failed"
            ? "解密失敗 — 請確認 passphrase 正確"
            : reason === "not_found"
              ? "雲端尚無此 bundle"
              : `下載失敗：${reason}`,
        );
        return;
      }
      const payload = (result as { payload?: unknown }).payload;
      const { applied, skipped } = await applyDownloaded(
        bundleType,
        payload,
        mergeStrategy,
      );
      toast.success(`已還原 ${bundleType}：套用 ${applied} 項，略過 ${skipped} 項`);
      await refreshManifest(provider, providerSub);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "下載失敗");
    }
  };

  if (isGuest || !user) {
    return (
      <NeonShell
        title="Monster Guardian 雲端同步"
        subtitle="端到端加密 · Google / GitHub 身份驗證"
        badge="Developed by Suckbob | Guardian Ai"
      >
        <NeonPanel className="space-y-4 max-w-md mx-auto text-center">
          <Shield className="w-10 h-10 mx-auto text-[var(--neon-cyan)]" />
          <p className="text-sm text-[var(--neon-muted)]">
            請先登入 Google 或 GitHub 帳戶以使用 E2E 雲端同步。訪客模式僅支援本機儲存。
          </p>
          <OAuthProviderButtons />
          <Button variant="outline" onClick={() => (window.location.href = "/login")}>
            前往登入頁
          </Button>
        </NeonPanel>
      </NeonShell>
    );
  }

  if (!provider) {
    return (
      <NeonShell
        title="Monster Guardian 雲端同步"
        subtitle="需要 Google 或 GitHub OAuth"
        badge="Developed by Suckbob | Guardian Ai"
      >
        <NeonPanel className="space-y-4 max-w-lg mx-auto">
          <p className="text-sm text-[var(--neon-muted)]">
            目前帳號（{user.loginMethod ?? "unknown"}）不支援 Guardian 雲端同步。
            請使用 Google 或 GitHub 重新登入。
          </p>
          <OAuthProviderButtons />
        </NeonPanel>
      </NeonShell>
    );
  }

  return (
    <NeonShell
      title="Monster Guardian 雲端同步"
      subtitle="OC 文案 · 對話 · 偏好 · 訓練 Vault — 全程端到端加密"
      badge="Developed by Suckbob | Guardian Ai"
    >
      <div className="grid lg:grid-cols-2 gap-4">
        <NeonPanel className="space-y-4">
          <h2 className="font-semibold text-[var(--neon-cyan)] flex items-center gap-2">
            <Shield className="w-4 h-4" /> 平台狀態
          </h2>
          <div className="flex flex-wrap gap-2 text-xs">
            <Badge variant={guardianOk ? "default" : "destructive"}>
              Guardian {guardianOk ? "就緒" : "離線"}
            </Badge>
            <Badge variant={online ? "default" : "secondary"}>
              API {online ? "連線" : "離線"}
            </Badge>
            <Badge variant="outline">{provider}</Badge>
          </div>
          <p className="text-xs text-[var(--neon-muted)]">{disclaimerLine}</p>
          {desktopVault && (
            <p className="text-xs text-[var(--neon-green)]">{desktopVault}</p>
          )}
          {tunnelUrl && (
            <p className="text-xs break-all text-[var(--neon-muted)]">
              Tunnel: {tunnelUrl}
            </p>
          )}
          <p className="text-xs font-mono text-[var(--neon-muted)]">
            sub: {providerSub.slice(0, 20)}…
          </p>
        </NeonPanel>

        <NeonPanel className="space-y-4">
          <h2 className="font-semibold text-[var(--neon-cyan)] flex items-center gap-2">
            <Lock className="w-4 h-4" /> E2E 金鑰
          </h2>
          <p className="text-xs text-[var(--neon-muted)]">
            輸入 ≥8 字 passphrase。金鑰僅存於您的記憶體，伺服器只保存密文。
            Google/GitHub 僅用於身份驗證。
          </p>
          <div>
            <Label className="text-xs">Passphrase</Label>
            <Input
              type="password"
              value={passphrase}
              onChange={(e) => setPassphrase(e.target.value)}
              placeholder="至少 8 個字元"
              autoComplete="off"
            />
          </div>
          <div>
            <Label className="text-xs">還原策略</Label>
            <Select
              value={mergeStrategy}
              onValueChange={(v) => setMergeStrategy(v as MergeStrategy)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="merge">合併（略過同名 OC）</SelectItem>
                <SelectItem value="replace">覆蓋（對話先清空再還原）</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </NeonPanel>

        <NeonPanel className="space-y-4 lg:col-span-2">
          <h2 className="font-semibold text-[var(--neon-cyan)] flex items-center gap-2">
            <Cloud className="w-4 h-4" /> 同步內容
          </h2>
          <div className="grid sm:grid-cols-2 gap-3">
            {BUNDLE_OPTIONS.map((opt) => (
              <label
                key={opt.id}
                className="flex items-start gap-3 p-3 rounded-lg border border-border/60 cursor-pointer hover:border-[var(--neon-cyan)]/40"
              >
                <Checkbox
                  checked={selected.has(opt.id)}
                  onCheckedChange={(c) => toggleBundle(opt.id, c === true)}
                />
                <div>
                  <p className="text-sm font-medium">{opt.label}</p>
                  <p className="text-xs text-muted-foreground">{opt.hint}</p>
                </div>
              </label>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              className="neon-btn-primary gap-2"
              disabled={!canSync || busy}
              onClick={() => void handleUpload()}
            >
              {busy ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <CloudUpload className="w-4 h-4" />
              )}
              加密上傳
            </Button>
            {BUNDLE_OPTIONS.filter((o) => selected.has(o.id)).map((opt) => (
              <Button
                key={`dl-${opt.id}`}
                variant="outline"
                size="sm"
                className="gap-1"
                disabled={!canSync || busy}
                onClick={() => void handleDownloadApply(opt.id)}
              >
                <CloudDownload className="w-3 h-3" />
                下載 {opt.label}
              </Button>
            ))}
          </div>
        </NeonPanel>

        <NeonPanel className="space-y-3 lg:col-span-2">
          <h2 className="font-semibold text-[var(--neon-cyan)] text-sm">
            雲端 Manifest
          </h2>
          {lastSync ? (
            <p className="text-xs text-[var(--neon-muted)]">
              上次同步：{new Date(lastSync).toLocaleString()}
            </p>
          ) : (
            <p className="text-xs text-[var(--neon-muted)]">尚無同步記錄</p>
          )}
          {bundles.length === 0 ? (
            <p className="text-xs text-muted-foreground">輸入 passphrase 後可查看已上傳 bundle</p>
          ) : (
            <ul className="text-xs space-y-1 font-mono">
              {bundles.map((b) => (
                <li key={`${b.type}-${b.uploaded_at}`} className="flex gap-2">
                  <span className="text-[var(--neon-cyan)]">{b.type}</span>
                  <span className="text-muted-foreground">
                    {new Date(b.uploaded_at).toLocaleString()}
                  </span>
                  {b.device_id && (
                    <span className="text-muted-foreground">· {b.device_id}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </NeonPanel>
      </div>
    </NeonShell>
  );
}