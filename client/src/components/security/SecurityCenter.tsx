import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Lock, Shield, Wifi, Usb, Loader2 } from "lucide-react";
import type { SecuritySnapshot } from "@/hooks/useSecurityStatus";

interface Props {
  snapshot: SecuritySnapshot | null;
  threatCount: number;
  locking: boolean;
  onLock: () => void;
  onRecover: (token: string) => void;
  onBack: () => void;
}

function StatusCard({
  title,
  icon: Icon,
  status,
  statusColor,
  children,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  status: string;
  statusColor: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="p-4 border-border/60 bg-card/70 hover:border-blue-500/30 transition-colors">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className="w-5 h-5 text-blue-400" />
          <h3 className="font-semibold text-sm">{title}</h3>
        </div>
        <span className={`text-xs font-medium ${statusColor}`}>{status}</span>
      </div>
      <div className="text-xs text-muted-foreground space-y-1">{children}</div>
    </Card>
  );
}

export default function SecurityCenter({
  snapshot,
  threatCount,
  locking,
  onLock,
  onRecover,
  onBack,
}: Props) {
  const [recoverToken, setRecoverToken] = useState("");
  const ml = snapshot?.monsterlock;
  const cg = snapshot?.crimeguard;

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Shield className="w-7 h-7 text-blue-400" />
            安全中心
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            MonsterShield · CrimeGuard 即時狀態
          </p>
        </div>
        <Button variant="outline" size="sm" className="rounded-full" onClick={onBack}>
          返回聊天
        </Button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {[
          { label: "今日威脅", value: threatCount },
          { label: "阻擋", value: cg?.blocks ?? 0 },
          { label: "鎖定觸發", value: cg?.locks_triggered ?? 0 },
        ].map((s) => (
          <Card key={s.label} className="p-3 text-center border-violet-500/15 bg-muted/20">
            <p className="text-2xl font-bold text-foreground">{s.value}</p>
            <p className="text-xs text-muted-foreground">{s.label}</p>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatusCard
          title="MonsterShield"
          icon={Shield}
          status={ml?.green_dot ? "保護中" : "待機"}
          statusColor={ml?.green_dot ? "text-emerald-400" : "text-amber-400"}
        >
          <p>強度：{ml?.strength || "—"}</p>
          <p>憑證輪替：{ml?.rapid_credential_shield?.generation ?? "—"} 代</p>
          <p>阻擋：{ml?.blocks ?? 0}</p>
        </StatusCard>

        <StatusCard
          title="CrimeGuard"
          icon={Lock}
          status={cg?.network_locked ? "已鎖定" : "監控中"}
          statusColor={cg?.network_locked ? "text-red-400" : "text-emerald-400"}
        >
          <p>規則：{cg?.rules_version || "hk-2026.06"}</p>
          <p>今日阻擋：{cg?.blocks ?? 0}</p>
          <p>模式：{cg?.lock_mode || "localhost_only"}</p>
        </StatusCard>

        <StatusCard
          title="設備聯繫監控"
          icon={Usb}
          status={cg?.device_contact_detected ? "偵測中" : "正常"}
          statusColor={cg?.device_contact_detected ? "text-amber-400" : "text-emerald-400"}
        >
          <p>類型：{cg?.device_contact_type || "無"}</p>
          <p>設備鎖定：{cg?.device_locked ? "是" : "否"}</p>
        </StatusCard>

        <StatusCard
          title="網絡鎖定"
          icon={Wifi}
          status={cg?.network_locked ? "ACTIVE" : "待命"}
          statusColor={cg?.network_locked ? "text-red-400" : "text-muted-foreground"}
        >
          <p>VPN 偵測：{cg?.vpn_detected ? cg.vpn_type || "是" : "否"}</p>
          <p>即使 VPN 亦有效（block_vpn_ports）</p>
        </StatusCard>
      </div>

      <div className="flex flex-wrap gap-3 py-3">
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="destructive"
              className="rounded-full gap-2"
              disabled={locking || cg?.network_locked}
            >
              {locking ? <Loader2 className="w-4 h-4 animate-spin" /> : <Lock className="w-4 h-4" />}
              立即網絡鎖定
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>確認立即網絡鎖定？</AlertDialogTitle>
              <AlertDialogDescription>
                將封鎖外網連線（含 VPN 端口），僅保留本機服務。
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>取消</AlertDialogCancel>
              <AlertDialogAction onClick={onLock}>確認鎖定</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        <div className="flex gap-2 items-center flex-1 min-w-[200px]">
          <Input
            placeholder="Recovery token 解除鎖定"
            value={recoverToken}
            onChange={(e) => setRecoverToken(e.target.value)}
            className="rounded-xl text-sm"
          />
          <Button
            variant="outline"
            className="rounded-xl shrink-0"
            onClick={() => onRecover(recoverToken)}
            disabled={!recoverToken.trim()}
          >
            解除
          </Button>
        </div>
      </div>

      <Tabs defaultValue="crimeguard">
        <TabsList className="rounded-xl">
          <TabsTrigger value="monsterlock">MonsterLock</TabsTrigger>
          <TabsTrigger value="crimeguard">CrimeGuard</TabsTrigger>
        </TabsList>
        {(["monsterlock", "crimeguard"] as const).map((key) => {
          const events = key === "monsterlock" ? ml?.events : cg?.events;
          const formatTs = (ts: number) =>
            ts ? new Date(ts * 1000).toLocaleString("zh-HK") : "—";
          return (
            <TabsContent key={key} value={key}>
              <ul className="text-xs space-y-1 max-h-48 overflow-y-auto">
                {(events || []).map((ev, i) => (
                  <li key={i} className="text-muted-foreground font-mono">
                    [{formatTs(ev.ts)}] {ev.message}
                  </li>
                ))}
                {(!events || events.length === 0) && (
                  <li className="text-muted-foreground">尚無事件</li>
                )}
              </ul>
            </TabsContent>
          );
        })}
      </Tabs>
    </div>
  );
}