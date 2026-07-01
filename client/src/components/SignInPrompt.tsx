import { useGuest } from "@/contexts/GuestContext";
import OAuthProviderButtons from "@/components/OAuthProviderButtons";
import { Button } from "@/components/ui/button";
import { useTranslation } from "react-i18next";
import { useLocation } from "wouter";

export default function SignInPrompt() {
  const { t } = useTranslation();
  const { setAsGuest } = useGuest();
  const [, setLocation] = useLocation();

  const handleLogin = () => {
    if (import.meta.env.DEV) {
      window.location.href = "/api/oauth/dev-login";
      return;
    }
    setLocation("/login");
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-background p-6 text-center">
      <p className="text-muted-foreground">{t("chat.signInRequired")}</p>
      <div className="flex flex-col items-center gap-4 w-full max-w-xs">
        <OAuthProviderButtons size="default" />
        <div className="flex flex-wrap items-center justify-center gap-3 w-full">
          <Button variant="secondary" onClick={handleLogin} className="flex-1">
            {t("auth.login", "登入")}
          </Button>
          <Button variant="outline" onClick={() => setAsGuest()} className="flex-1">
            {t("auth.continueAsGuest", "以訪客身份繼續")}
          </Button>
        </div>
      </div>
    </div>
  );
}