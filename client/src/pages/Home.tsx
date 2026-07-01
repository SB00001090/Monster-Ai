import { useAuth } from "@/_core/hooks/useAuth";
import { useGuest } from "@/contexts/GuestContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { trpc } from "@/lib/trpc";
import { useLocation } from "wouter";
import { useTranslation } from "react-i18next";
import {
  MessageCircle,
  Users,
  Image as ImageIcon,
  Film,
  BookOpen,
  MessageSquare,
  Cpu,
  ArrowRight,
  Activity,
  Sparkles,
  Download,
} from "lucide-react";
import LatestCharactersShowcase from "@/components/LatestCharactersShowcase";

const quickLinks = [
  { icon: MessageCircle, labelKey: "navigation.chatWithCharacter", path: "/character-chat", color: "text-violet-400" },
  { icon: Users, labelKey: "navigation.createCharacter", path: "/characters", color: "text-blue-400" },
  { icon: ImageIcon, labelKey: "home.textToImage", path: "/text-to-image", color: "text-pink-400" },
  { icon: Film, labelKey: "navigation.video", path: "/video", color: "text-orange-400" },
  { icon: Sparkles, labelKey: "navigation.miniStudio", path: "/mini-studio", color: "text-fuchsia-400" },
  { icon: Download, labelKey: "navigation.ecosystem", path: "/ecosystem", color: "text-cyan-400" },
  { icon: BookOpen, labelKey: "navigation.templates", path: "/templates", color: "text-emerald-400" },
  { icon: MessageSquare, labelKey: "navigation.forum", path: "/forum", color: "text-cyan-400" },
];

export default function Home() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { isGuest } = useGuest();
  const [, navigate] = useLocation();

  const healthQuery = trpc.system.health.useQuery({ timestamp: Date.now() });
  const charactersQuery = trpc.characters.getMyCharacters.useQuery();
  const conversationsQuery = trpc.chat.getConversations.useQuery(undefined, {
    enabled: Boolean(user) || isGuest,
  });

  const pythonOk = healthQuery.data?.python?.ok ?? false;
  const characterCount = charactersQuery.data?.length ?? 0;
  const conversationCount = conversationsQuery.data?.length ?? 0;

  return (
    <div className="flex-1 overflow-auto p-6 space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-foreground">
          {user ? t("home.welcomeUser", { name: user.name }) : t("home.welcomeGuest")}
        </h1>
        <p className="text-muted-foreground mt-2">{t("home.subtitle")}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2">
              <Activity className="w-4 h-4" />
              {t("home.pythonBackend")}
            </CardDescription>
            <CardTitle className="text-lg">
              <Badge variant={pythonOk ? "default" : "destructive"}>
                {pythonOk ? t("home.online") : t("home.offline")}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            {pythonOk && healthQuery.data?.python?.backend
              ? `LLM: ${healthQuery.data.python.backend}`
              : t("home.startPythonHint")}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("home.myCharacters")}</CardDescription>
            <CardTitle className="text-3xl">{characterCount}</CardTitle>
          </CardHeader>
          <CardContent>
            <Button variant="link" className="p-0 h-auto" onClick={() => navigate("/characters")}>
              {t("home.manageCharacters")} <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>{t("home.conversations")}</CardDescription>
            <CardTitle className="text-3xl">{conversationCount}</CardTitle>
          </CardHeader>
          <CardContent>
            <Button variant="link" className="p-0 h-auto" onClick={() => navigate("/character-chat")}>
              {t("home.startChat")} <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </CardContent>
        </Card>
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-4">{t("home.quickActions")}</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {quickLinks.map((link) => (
            <Card
              key={link.path}
              className="cursor-pointer hover:border-accent/50 transition-colors"
              onClick={() => navigate(link.path)}
            >
              <CardContent className="pt-6 pb-4 flex flex-col items-center text-center gap-2">
                <link.icon className={`w-8 h-8 ${link.color}`} />
                <span className="text-sm font-medium">{t(link.labelKey)}</span>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      <LatestCharactersShowcase />

      <Card className="border-accent/20 bg-accent/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Cpu className="w-5 h-5" />
            {t("home.devTipsTitle")}
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-1">
          <p>{t("home.devTip1")}</p>
          <p>{t("home.devTip2")}</p>
          <p>{t("home.devTip3")}</p>
        </CardContent>
      </Card>
    </div>
  );
}