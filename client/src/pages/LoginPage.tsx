import { useGuest } from "@/contexts/GuestContext";
import OAuthProviderButtons from "@/components/OAuthProviderButtons";
import { getOAuthLoginUrl, isOAuthConfigured } from "@/const";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useTranslation } from "react-i18next";
import { useLocation } from "wouter";
import { APP_LOGO_SRC } from "@/const";

export default function LoginPage() {
  const { t } = useTranslation();
  const { setAsGuest } = useGuest();
  const [, setLocation] = useLocation();

  const handleGuestMode = () => {
    setAsGuest();
    setLocation("/");
  };

  const oauthConfigured = isOAuthConfigured();
  const isDev = import.meta.env.DEV;

  const handleLogin = () => {
    if (!oauthConfigured) {
      if (isDev) {
        window.location.href = "/api/oauth/dev-login";
        return;
      }
      handleGuestMode();
      return;
    }
    window.location.href = getOAuthLoginUrl();
  };

  const handleDevLogin = () => {
    window.location.href = "/api/oauth/dev-login";
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <img
              src={APP_LOGO_SRC}
              alt="MonsterAi"
              className="w-20 h-20 rounded-2xl object-cover shadow-lg shadow-violet-500/20"
            />
          </div>
          <CardTitle className="text-3xl font-bold">Monster Guardian AI</CardTitle>
          <CardDescription className="mt-2">
            {t("common.welcome") || "本地優先 · 端到端加密雲端同步"}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="space-y-3">
            <OAuthProviderButtons />

            <Button
              onClick={handleLogin}
              variant="secondary"
              className="w-full gap-2"
              size="lg"
            >
              {oauthConfigured
                ? (t("auth.login") || "其他方式登入")
                : (t("auth.devLogin") || "Dev Sign In")}
            </Button>

            {isDev && oauthConfigured && (
              <Button
                onClick={handleDevLogin}
                variant="secondary"
                className="w-full gap-2"
                size="lg"
              >
                {t("auth.devLogin") || "Dev Sign In (local)"}
              </Button>
            )}

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-border"></div>
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-muted-foreground">
                  {t("common.or") || "Or"}
                </span>
              </div>
            </div>

            <Button
              onClick={handleGuestMode}
              variant="outline"
              className="w-full gap-2"
              size="lg"
            >
              {t("auth.continueAsGuest") || "Continue as Guest"}
            </Button>
          </div>

          <div className="bg-muted p-4 rounded-lg text-sm text-muted-foreground space-y-2">
            <p className="font-semibold">{t("auth.guestModeInfo") || "Guest Mode:"}</p>
            <ul className="list-disc list-inside space-y-1 text-xs">
              <li>{t("auth.guestFeature1") || "Chat with AI characters"}</li>
              <li>{t("auth.guestFeature2") || "Generate images"}</li>
              <li>{t("auth.guestFeature3") || "Data stored locally only"}</li>
              <li>{t("auth.guestFeature4") || "Login anytime to save data"}</li>
            </ul>
          </div>

          <p className="text-xs text-center text-muted-foreground">
            {t("auth.guestDisclaimer") || "Guest data will be lost if you clear your browser cache"}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
