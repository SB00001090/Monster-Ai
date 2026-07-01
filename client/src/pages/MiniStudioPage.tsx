import { useCallback, useEffect, useState } from "react";
import { NeonPanel, NeonShell } from "@/components/NeonShell";
import { QualityRing, qualityFromResult } from "@/components/QualityRing";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useBackend } from "@/contexts/BackendContext";
import { getGenProvider } from "@/lib/integrations";
import { monsterApi } from "@/lib/monsterApi";
import { toast } from "sonner";
import { ImageIcon, Mic, Sparkles } from "lucide-react";

type Ref = { id: string; name: string };

const LOCALES = [
  { id: "zh-TW", label: "繁體" },
  { id: "zh-HK", label: "粵語" },
  { id: "zh-CN", label: "简体" },
  { id: "ja", label: "日本語" },
  { id: "en", label: "EN" },
];

const STABLE_TEMPLATE = "stable";

export default function MiniStudioPage() {
  const { online } = useBackend();
  const [tab, setTab] = useState<"r18" | "likeness" | "multi">("r18");
  const [prompt, setPrompt] = useState("");
  const [locale, setLocale] = useState("zh-TW");
  const [refs, setRefs] = useState<Ref[]>([]);
  const [refId, setRefId] = useState("");
  const [voiceText, setVoiceText] = useState("");
  const [preview, setPreview] = useState("");
  const [quality, setQuality] = useState<{ score?: number; passed?: boolean }>({});
  const [providerLabel, setProviderLabel] = useState("monster");
  const [stats, setStats] = useState("");
  const [busy, setBusy] = useState(false);
  const [refName, setRefName] = useState("");
  const [refFile, setRefFile] = useState<File | null>(null);

  const refresh = useCallback(async () => {
    try {
      const info = await monsterApi.miniInfo();
      setRefs((info.references as Ref[]) || []);
      const s = await monsterApi.miniSuccess();
      const rate = ((Number(s.success_rate) || 0) * 100).toFixed(1);
      const sim =
        s.avg_likeness_similarity != null
          ? (Number(s.avg_likeness_similarity) * 100).toFixed(1)
          : "—";
      setStats(`成功率 ${rate}% · Likeness ${sim}% · 門檻 70%`);
    } catch {
      /* backend optional */
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const uploadRef = async () => {
    if (!refFile || !refName.trim()) {
      toast.error("請填寫角色名稱並選擇參考圖");
      return;
    }
    const fd = new FormData();
    fd.append("name", refName.trim());
    fd.append("image", refFile);
    setBusy(true);
    try {
      const r = await monsterApi.uploadReference(fd);
      toast.success(`已上傳: ${r.id || refName}`);
      setRefId(String(r.id || ""));
      refresh();
    } catch (e) {
      toast.error(String(e));
    } finally {
      setBusy(false);
    }
  };

  const run = async () => {
    if (!prompt.trim()) return;
    setBusy(true);
    setPreview("");
    setQuality({});
    const provider = getGenProvider();
    setProviderLabel(provider);
    try {
      let res: Record<string, unknown>;
      if (tab === "r18") {
        if (provider === "dify") {
          res = await monsterApi.difyGenerate({
            prompt,
            locale,
            template_id: STABLE_TEMPLATE,
          });
        } else {
          res = await monsterApi.miniGenerate({
            prompt,
            locale,
            template_id: STABLE_TEMPLATE,
          });
        }
      } else if (tab === "likeness") {
        if (!refId) throw new Error("請選擇參考");
        res = await monsterApi.miniLikeness({
          prompt,
          reference_id: refId,
          locale,
          template_id: "idol_likeness",
        });
      } else {
        if (!refId) throw new Error("請選擇參考");
        res = await monsterApi.miniMultimodal({
          prompt,
          reference_id: refId,
          voice_text: voiceText || undefined,
          locale,
        });
      }
      const src = String(res.url || res.path || "");
      if (src) setPreview(src.startsWith("http") ? src : src.startsWith("/") ? src : `/${src}`);
      setQuality(qualityFromResult(res));
      const q = qualityFromResult(res);
      if (q.passed === false || (q.score != null && q.score < 0.7)) {
        toast.warning("品質低於 70% — 已記錄並可重試");
      } else {
        toast.success("生成完成");
      }
      refresh();
    } catch (e) {
      toast.error(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <NeonShell
      title="MINI STUDIO"
      subtitle="R18+ 圖像 · 極度相似 Likeness · 圖+音多模態 · 品質門檻 70%"
      badge={stats || "Mini Monster AI v1.0"}
    >
      {!online && (
        <NeonPanel className="border-[var(--neon-pink)] text-sm text-[var(--neon-pink)]">
          後端離線 — 本機請執行 python main.py，或設定 Cloudflare Tunnel URL
        </NeonPanel>
      )}

      <div className="flex flex-wrap gap-2">
        {(
          [
            ["r18", "R18+ 圖像", ImageIcon],
            ["likeness", "偶像 Likeness", Sparkles],
            ["multi", "圖+音多模態", Mic],
          ] as const
        ).map(([id, label, Icon]) => (
          <Button
            key={id}
            variant={tab === id ? "default" : "outline"}
            size="sm"
            onClick={() => setTab(id)}
            className={tab === id ? "neon-btn-primary" : ""}
          >
            <Icon className="w-4 h-4 mr-1" />
            {label}
          </Button>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <NeonPanel className="space-y-3">
          {(tab === "likeness" || tab === "multi") && (
            <>
              <div className="grid sm:grid-cols-2 gap-2">
                <div>
                  <Label className="text-xs">角色名稱</Label>
                  <Input value={refName} onChange={(e) => setRefName(e.target.value)} />
                </div>
                <div>
                  <Label className="text-xs">參考臉圖</Label>
                  <Input
                    type="file"
                    accept="image/*"
                    onChange={(e) => setRefFile(e.target.files?.[0] || null)}
                  />
                </div>
              </div>
              <Button variant="outline" size="sm" disabled={busy} onClick={uploadRef}>
                上傳參考（需有權使用）
              </Button>
              <div>
                <Label className="text-xs">已選參考</Label>
                <Select value={refId} onValueChange={setRefId}>
                  <SelectTrigger>
                    <SelectValue placeholder="選擇參考" />
                  </SelectTrigger>
                  <SelectContent>
                    {refs.map((r) => (
                      <SelectItem key={r.id} value={r.id}>
                        {r.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </>
          )}
          <div>
            <Label className="text-xs">語言</Label>
            <Select value={locale} onValueChange={setLocale}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LOCALES.map((l) => (
                  <SelectItem key={l.id} value={l.id}>
                    {l.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">提示詞</Label>
            <Textarea
              rows={4}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="多語言場景描述…"
            />
          </div>
          {tab === "multi" && (
            <div>
              <Label className="text-xs">語音台詞（可選）</Label>
              <Input value={voiceText} onChange={(e) => setVoiceText(e.target.value)} />
            </div>
          )}
          <Button className="neon-btn-primary w-full" disabled={busy || !online} onClick={run}>
            生成 {tab === "r18" ? `(${providerLabel})` : ""}
          </Button>
          <p className="text-[10px] text-[var(--neon-muted)]">
            模板 stable · 低於 70% 自動重試。R18+ 僅限成年用戶本地私人使用。
          </p>
        </NeonPanel>

        <NeonPanel>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm text-[var(--neon-cyan)]">預覽</h3>
            {(quality.score != null || quality.passed != null) && (
              <QualityRing
                score={quality.score}
                passed={quality.passed}
                size={48}
                label="品質"
              />
            )}
          </div>
          {preview ? (
            <img src={preview} alt="preview" className="w-full rounded-lg border border-[var(--neon-border)]" />
          ) : (
            <div className="aspect-square rounded-lg border border-dashed border-[var(--neon-border)] flex items-center justify-center text-[var(--neon-muted)] text-sm">
              尚無輸出
            </div>
          )}
        </NeonPanel>
      </div>
    </NeonShell>
  );
}