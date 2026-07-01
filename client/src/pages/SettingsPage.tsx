import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { useAuth } from "@/_core/hooks/useAuth";
import { useTheme } from "@/contexts/ThemeContext";
import { useGuest } from "@/contexts/GuestContext";
import OAuthProviderButtons from "@/components/OAuthProviderButtons";
import LLMSettings from "./LLMSettings";
import { useLocation } from "wouter";

type SettingsTab = "profile" | "theme" | "llm" | "safety" | "account";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("profile");
  const { user } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { isGuest } = useGuest();

  const tabs = [
    { id: "profile" as const, label: "個人資料", icon: "👤" },
    { id: "theme" as const, label: "主題外觀", icon: "🎨" },
    { id: "llm" as const, label: "LLM 模型", icon: "🤖" },
    { id: "safety" as const, label: "安全設定", icon: "🛡️" },
    { id: "account" as const, label: "帳號管理", icon: "⚙️" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-foreground">設定</h2>
        <p className="text-muted-foreground mt-1">管理您的個人偏好和系統配置</p>
      </div>

      {/* Tab Navigation */}
      <div className="flex flex-wrap gap-2 border-b border-border pb-3">
        {tabs.map((tab) => (
          <Button
            key={tab.id}
            variant={activeTab === tab.id ? "default" : "ghost"}
            size="sm"
            onClick={() => setActiveTab(tab.id)}
            className="gap-2"
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </Button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "profile" && <ProfileSection user={user} isGuest={isGuest} />}
      {activeTab === "theme" && <ThemeSection theme={theme} toggleTheme={toggleTheme} />}
      {activeTab === "llm" && <LLMSettings />}
      {activeTab === "safety" && <SafetySection />}
      {activeTab === "account" && <AccountSection user={user} isGuest={isGuest} />}
    </div>
  );
}

function ProfileSection({ user, isGuest }: { user: any; isGuest: boolean }) {
  const [displayName, setDisplayName] = useState(user?.name || "");

  return (
    <Card>
      <CardHeader>
        <CardTitle>個人資料</CardTitle>
        <CardDescription>管理您的顯示名稱和個人資訊</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center text-2xl">
            {isGuest ? "👻" : user?.name?.[0]?.toUpperCase() || "U"}
          </div>
          <div>
            <p className="font-medium">{isGuest ? "臨時訪客" : user?.name || "用戶"}</p>
            <Badge variant={isGuest ? "secondary" : "default"}>
              {isGuest ? "臨時帳號" : "正式帳號"}
            </Badge>
          </div>
        </div>

        <div className="space-y-2">
          <Label>顯示名稱</Label>
          <Input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="輸入您的顯示名稱"
            disabled={isGuest}
          />
          {isGuest && (
            <p className="text-xs text-muted-foreground">臨時帳號無法修改個人資料，請登入正式帳號</p>
          )}
        </div>

        {!isGuest && (
          <Button
            onClick={() => toast.success("個人資料已更新")}
            disabled={!displayName.trim()}
          >
            保存變更
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

function ThemeSection({ theme, toggleTheme }: { theme: string; toggleTheme?: () => void }) {
  const themes = [
    { id: "dark", label: "深色模式", icon: "🌙", description: "護眼深色主題" },
    { id: "light", label: "淺色模式", icon: "☀️", description: "明亮淺色主題" },
    { id: "system", label: "跟隨系統", icon: "💻", description: "自動跟隨系統設定" },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>主題外觀</CardTitle>
        <CardDescription>選擇您喜歡的介面主題</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {themes.map((t) => (
            <div
              key={t.id}
              className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                theme === t.id
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/50"
              }`}
              onClick={() => {
                if (toggleTheme) toggleTheme();
                toast.success(`主題已切換`);
              }}
            >
              <div className="text-center">
                <div className="text-3xl mb-2">{t.icon}</div>
                <div className="font-medium">{t.label}</div>
                <div className="text-xs text-muted-foreground mt-1">{t.description}</div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function SafetySection() {
  const [contentFilter, setContentFilter] = useState("strict");

  const filterLevels = [
    { id: "strict", label: "嚴格", description: "封鎖所有不當內容（推薦）", icon: "🔒" },
    { id: "moderate", label: "適中", description: "封鎖明確違規內容", icon: "⚠️" },
    { id: "minimal", label: "最低", description: "僅封鎖涉及未成年人的內容", icon: "🔓" },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>安全設定</CardTitle>
        <CardDescription>配置內容安全過濾等級</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-3">
          {filterLevels.map((level) => (
            <div
              key={level.id}
              className={`p-4 rounded-lg border cursor-pointer transition-all ${
                contentFilter === level.id
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/50"
              }`}
              onClick={() => {
                setContentFilter(level.id);
                toast.success(`內容過濾等級已設為「${level.label}」`);
              }}
            >
              <div className="flex items-center gap-3">
                <span className="text-xl">{level.icon}</span>
                <div>
                  <div className="font-medium">{level.label}</div>
                  <div className="text-xs text-muted-foreground">{level.description}</div>
                </div>
                {contentFilter === level.id && (
                  <Badge className="ml-auto">目前</Badge>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="p-3 bg-destructive/10 rounded-lg border border-destructive/20">
          <p className="text-sm text-destructive font-medium">⚠️ 不可更改的規則</p>
          <p className="text-xs text-muted-foreground mt-1">
            無論安全等級如何設定，系統始終禁止生成涉及未成年人的不當內容。此規則不可繞過。
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

function AccountSection({ user, isGuest }: { user: any; isGuest: boolean }) {
  const [, setLocation] = useLocation();

  return (
    <Card>
      <CardHeader>
        <CardTitle>帳號管理</CardTitle>
        <CardDescription>管理您的帳號狀態和數據</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isGuest ? (
          <div className="space-y-4">
            <div className="p-4 bg-amber-500/10 rounded-lg border border-amber-500/20">
              <p className="font-medium text-amber-600">👻 您目前使用臨時帳號</p>
              <p className="text-sm text-muted-foreground mt-1">
                臨時帳號的數據可能在一段時間後被清除。建議登入正式帳號以保留所有數據。
              </p>
            </div>
            <div className="space-y-2">
              <h4 className="font-medium">臨時帳號限制：</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• 聊天記錄可能在 7 天後過期</li>
                <li>• 無法分享角色到社群</li>
                <li>• 無法使用進階 AI Agent 功能</li>
                <li>• 存儲空間有限</li>
              </ul>
            </div>
            <OAuthProviderButtons size="default" />
            <Button className="w-full" variant="outline" onClick={() => setLocation("/login")}>
              前往登入頁
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="p-4 bg-green-500/10 rounded-lg border border-green-500/20">
              <p className="font-medium text-green-600">✅ 正式帳號</p>
              <p className="text-sm text-muted-foreground mt-1">
                您的所有數據都已安全保存。享受完整功能。
              </p>
            </div>

            <Button
              className="w-full"
              variant="secondary"
              onClick={() => setLocation("/guardian-sync")}
            >
              🛡️ Monster Guardian 雲端同步
            </Button>

            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 rounded-lg border">
                <p className="text-xs text-muted-foreground">帳號 ID</p>
                <p className="font-mono text-sm">{user?.id || "N/A"}</p>
              </div>
              <div className="p-3 rounded-lg border">
                <p className="text-xs text-muted-foreground">角色</p>
                <p className="text-sm">{user?.role === "admin" ? "管理員" : "用戶"}</p>
              </div>
              <div className="p-3 rounded-lg border">
                <p className="text-xs text-muted-foreground">註冊時間</p>
                <p className="text-sm">{user?.createdAt ? new Date(user.createdAt).toLocaleDateString() : "N/A"}</p>
              </div>
              <div className="p-3 rounded-lg border">
                <p className="text-xs text-muted-foreground">帳號狀態</p>
                <Badge variant="default">活躍</Badge>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
