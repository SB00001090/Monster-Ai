import { Toaster } from "sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/NotFound";
import ChatPage from "@/pages/ChatPage";
import Home from "@/pages/Home";
import MobileApp from "@/pages/MobileApp";
import SelfAwarenessPage from "@/pages/SelfAwarenessPage";
import CharacterManagementPage from "./pages/CharacterManagementPage";
import CharacterTemplatesPage from "./pages/CharacterTemplatesPage";
import CharacterCommunityPage from "./pages/CharacterCommunityPage";
import CharacterAnalyticsPage from "./pages/CharacterAnalyticsPage";
import DashboardLayout from "./components/DashboardLayout";
import TutorialPage from "./pages/TutorialPage";
import AdminBugDashboard from "./pages/AdminBugDashboard";
import LoginPage from "./pages/LoginPage";
import LLMSettings from "./pages/LLMSettings";
import AgentPage from "./pages/AgentPage";
import SettingsPage from "./pages/SettingsPage";
import ForumPage from "./pages/ForumPage";
import MusicPage from "./pages/MusicPage";
import { F2FVerificationPage } from "./pages/F2FVerificationPage";
import { TextToImagePage } from "./pages/TextToImagePage";
import { VideoGenerationPage } from "./pages/VideoGenerationPage";
import EcosystemPage from "./pages/EcosystemPage";
import MiniStudioPage from "./pages/MiniStudioPage";
import DeployPage from "./pages/DeployPage";
import IntegrationsPage from "./pages/IntegrationsPage";
import GuardianSyncPage from "./pages/GuardianSyncPage";
import NetworkLearningPanel from "./pages/NetworkLearningPanel";
import { BackendProvider } from "./contexts/BackendContext";

import LoadingScreen from "./components/LoadingScreen";
import { AgeVerification } from "./components/AgeVerification";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import { GuestProvider } from "./contexts/GuestContext";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "./_core/hooks/useAuth";
import { useGuest } from "./contexts/GuestContext";
import { usePushNotifications } from "./hooks/usePushNotifications";

function Router() {
  const [isMobile, setIsMobile] = useState(false);
  const [authTimedOut, setAuthTimedOut] = useState(false);
  const { user, loading: authLoading } = useAuth();
  const { isGuest, setAsGuest } = useGuest();
  usePushNotifications(); // Initialize push notifications

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  useEffect(() => {
    if (!authLoading) {
      setAuthTimedOut(false);
      return;
    }
    const t = window.setTimeout(() => setAuthTimedOut(true), 4000);
    return () => window.clearTimeout(t);
  }, [authLoading]);

  // Local + Cloudflare Pages: default guest when auth is unavailable or unset
  useEffect(() => {
    if (typeof window === "undefined") return;
    const host = window.location.hostname;
    const autoGuestHost =
      host.includes("pages.dev") || host === "localhost" || host === "127.0.0.1";
    if (!autoGuestHost) return;
    if (authLoading && !authTimedOut) return;
    if (!isGuest && !user) setAsGuest();
  }, [isGuest, user, setAsGuest, authLoading, authTimedOut]);

  // Avoid infinite splash when Node tRPC is slow/offline (common cause of "卡住")
  if (authLoading && !authTimedOut) {
    return <LoadingScreen onComplete={() => setAuthTimedOut(true)} />;
  }

  return (
    <Switch>
      <Route path="/login" component={LoginPage} />
      <Route path="/chat" component={ChatPage} />
      <Route path="/characters">
        <DashboardLayout>
          <CharacterManagementPage />
        </DashboardLayout>
      </Route>
      <Route path="/characters/new">
        <DashboardLayout>
          <CharacterManagementPage />
        </DashboardLayout>
      </Route>
      <Route path="/templates">
        <DashboardLayout>
          <CharacterTemplatesPage />
        </DashboardLayout>
      </Route>
      <Route path="/community">
        <DashboardLayout>
          <CharacterCommunityPage />
        </DashboardLayout>
      </Route>
      <Route path="/analytics">
        <DashboardLayout>
          <CharacterAnalyticsPage />
        </DashboardLayout>
      </Route>
      <Route path="/character-chat" component={ChatPage} />
      <Route path="/self-awareness">
        <DashboardLayout>
          <SelfAwarenessPage />
        </DashboardLayout>
      </Route>
      <Route path="/llm-settings">
        <DashboardLayout>
          <LLMSettings />
        </DashboardLayout>
      </Route>
      <Route path="/agent">
        <DashboardLayout>
          <AgentPage />
        </DashboardLayout>
      </Route>
      <Route path="/settings">
        <DashboardLayout>
          <SettingsPage />
        </DashboardLayout>
      </Route>
      <Route path="/forum">
        <DashboardLayout>
          <ForumPage />
        </DashboardLayout>
      </Route>
      <Route path="/music">
        <DashboardLayout>
          <MusicPage />
        </DashboardLayout>
      </Route>
      <Route path="/verify">
        <DashboardLayout>
          <F2FVerificationPage />
        </DashboardLayout>
      </Route>
      <Route path="/text-to-image">
        <DashboardLayout>
          <TextToImagePage />
        </DashboardLayout>
      </Route>
      <Route path="/video">
        <DashboardLayout>
          <VideoGenerationPage />
        </DashboardLayout>
      </Route>
      <Route path="/mini-studio">
        <DashboardLayout>
          <MiniStudioPage />
        </DashboardLayout>
      </Route>
      <Route path="/ecosystem">
        <DashboardLayout>
          <EcosystemPage />
        </DashboardLayout>
      </Route>
      <Route path="/deploy">
        <DashboardLayout>
          <DeployPage />
        </DashboardLayout>
      </Route>
      <Route path="/integrations">
        <DashboardLayout>
          <IntegrationsPage />
        </DashboardLayout>
      </Route>
      <Route path="/guardian-sync">
        <DashboardLayout>
          <GuardianSyncPage />
        </DashboardLayout>
      </Route>
      <Route path="/network-learning">
        <DashboardLayout>
          <NetworkLearningPanel />
        </DashboardLayout>
      </Route>

      <Route path="/home">
        <DashboardLayout>
          <Home />
        </DashboardLayout>
      </Route>
      <Route path="/tutorials" component={TutorialPage} />
      <Route path="/admin/bugs" component={AdminBugDashboard} />
      <Route path="/404" component={NotFound} />
      <Route path="/">
        {isMobile ? <MobileApp /> : <ChatPage />}
      </Route>
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  const [showLoading, setShowLoading] = useState(true);
  const [hasShownLoading, setHasShownLoading] = useState(() => {
    // Only show loading once per session
    return sessionStorage.getItem("monsterai_loaded") === "true";
  });

  const handleLoadingComplete = useCallback(() => {
    setShowLoading(false);
    sessionStorage.setItem("monsterai_loaded", "true");
  }, []);

  if (hasShownLoading) {
    // Skip loading screen if already shown this session
    return (
      <AgeVerification>
        <ErrorBoundary>
          <GuestProvider>
            <ThemeProvider defaultTheme="dark" switchable>
              <BackendProvider>
                <TooltipProvider>
                  <Toaster />
                  <Router />
                </TooltipProvider>
              </BackendProvider>
            </ThemeProvider>
          </GuestProvider>
        </ErrorBoundary>
      </AgeVerification>
    );
  }

  return (
    <AgeVerification>
      <ErrorBoundary>
        <GuestProvider>
          <ThemeProvider defaultTheme="dark" switchable>
            <BackendProvider>
              <TooltipProvider>
                {showLoading && <LoadingScreen onComplete={handleLoadingComplete} />}
                {!showLoading && (
                  <>
                    <Toaster />
                    <Router />
                  </>
                )}
              </TooltipProvider>
            </BackendProvider>
          </ThemeProvider>
        </GuestProvider>
      </ErrorBoundary>
    </AgeVerification>
  );
}

export default App;
