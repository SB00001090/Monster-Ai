import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/_core/hooks/useAuth";
import { useGuest } from "@/contexts/GuestContext";
import { useLocation } from "wouter";
import { trpc } from "@/lib/trpc";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import CharacterAvatar from "@/components/CharacterAvatar";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import ThemeSwitcher from "@/components/ThemeSwitcher";
import {
  BookOpen,
  Image as ImageIcon,
  Loader2,
  MessageCircle,
  MessageSquare,
  Plus,
  Search,
  Send,
  Shield,
  Sparkles,
  User,
  Volume2,
  VolumeX,
} from "lucide-react";
import SecurityStatusBar from "@/components/security/SecurityStatusBar";
import SecurityCenter from "@/components/security/SecurityCenter";
import CallGuardDownload from "@/components/security/CallGuardDownload";
import SafeModeToggle from "@/components/security/SafeModeToggle";
import { useSecurityStatus } from "@/hooks/useSecurityStatus";
import { toast } from "sonner";
import { Streamdown } from "streamdown";
import { useTranslation } from "react-i18next";
import { useTTS } from "@/hooks/useTTS";
import { APP_LOGO_SRC } from "@/const";
import SignInPrompt from "@/components/SignInPrompt";


interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  createdAt: Date;
}

interface Character {
  id: number;
  name: string;
  description: string;
  worldview: string;
  openingLine: string;
  averageRating: number;
  usageCount: number;
  avatarUrl?: string | null;
}

type ConversationItem = {
  id: number;
  title: string;
  mode: "chat" | "image";
  characterId?: number;
  messageCount?: number;
  lastMessage?: string | null;
  character?: Character | null;
};

const LAST_CONV_KEY = "monster_last_character_chat";

export default function ChatPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { isGuest } = useGuest();
  const canChat = Boolean(user) || isGuest;
  const [, navigate] = useLocation();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { speak, stop, isPlaying } = useTTS();
  const [playingMessageId, setPlayingMessageId] = useState<number | null>(null);

  const [selectedCharacterId, setSelectedCharacterId] = useState<number | null>(null);
  const [selectedCharacter, setSelectedCharacter] = useState<Character | null>(null);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [sidebarDraft, setSidebarDraft] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showWelcome, setShowWelcome] = useState(true);
  const [showSecurity, setShowSecurity] = useState(false);

  const security = useSecurityStatus();

  const myCharactersQuery = trpc.characters.getMyCharacters.useQuery(undefined, {
    enabled: canChat,
  });
  const publicCharactersQuery = trpc.characters.getPublic.useQuery(undefined, {
    enabled: canChat,
  });
  const conversationsQuery = trpc.chat.getConversations.useQuery(undefined, {
    enabled: canChat,
  });

  const { data: chatMessagesData } = trpc.chat.getMessages.useQuery(
    { conversationId: conversationId! },
    { enabled: !!conversationId }
  );
  const createConversationMutation = trpc.chat.createConversation.useMutation();
  const sendMessageMutation = trpc.chat.sendMessage.useMutation();

  const allCharacters = [
    ...(myCharactersQuery.data || []),
    ...(publicCharactersQuery.data || []).filter(
      (pc) => !myCharactersQuery.data?.some((mc) => mc.id === pc.id)
    ),
  ] as Character[];

  const chatHistory = ((conversationsQuery.data ?? []) as ConversationItem[]).filter(
    (c) => c.mode === "chat"
  );

  const resumeConversation = useCallback((conv: ConversationItem) => {
    setConversationId(conv.id);
    setShowWelcome(false);
    if (conv.character) {
      setSelectedCharacter(conv.character);
      setSelectedCharacterId(conv.character.id);
    } else {
      setSelectedCharacter(null);
      setSelectedCharacterId(null);
    }
  }, []);

  useEffect(() => {
    if (!conversationId || !chatMessagesData) {
      if (!conversationId) setMessages([]);
      return;
    }
    setMessages(
      chatMessagesData.map((msg) => ({
        id: msg.id,
        role: msg.role as "user" | "assistant",
        content: msg.content,
        createdAt: new Date(msg.createdAt),
      }))
    );
  }, [conversationId, chatMessagesData]);

  useEffect(() => {
    if (conversationId) {
      localStorage.setItem(LAST_CONV_KEY, String(conversationId));
    }
  }, [conversationId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendToConversation = useCallback(
    async (convId: number, text: string, characterId?: number | null) => {
      setIsLoading(true);
      try {
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now(),
            role: "user",
            content: text,
            createdAt: new Date(),
          },
        ]);
        const result = await sendMessageMutation.mutateAsync({
          conversationId: convId,
          message: text,
          characterId: characterId ?? undefined,
        });
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now() + 1,
            role: "assistant",
            content: result.message,
            createdAt: new Date(),
          },
        ]);
        conversationsQuery.refetch();
      } catch {
        toast.error(t("chat.failedToSend"));
        setMessages((prev) => prev.slice(0, -1));
      } finally {
        setIsLoading(false);
      }
    },
    [conversationsQuery, sendMessageMutation, t]
  );

  const startGeneralChat = useCallback(
    async (seed?: string) => {
      if (!canChat) {
        toast.error(t("chat.signInRequired"));
        return;
      }
      try {
        const conv = await createConversationMutation.mutateAsync({
          title: "Monster AI Chat",
          mode: "chat",
        });
        setConversationId(conv.id);
        setSelectedCharacter(null);
        setSelectedCharacterId(null);
        setShowWelcome(false);
        setMessages([]);
        await conversationsQuery.refetch();
        toast.success(t("chat.newConversation"));
        if (seed?.trim()) {
          await sendToConversation(conv.id, seed.trim());
        }
      } catch {
        toast.error(t("chat.failedToStart"));
      }
    },
    [canChat, createConversationMutation, conversationsQuery, sendToConversation, t]
  );

  const handleSelectCharacter = useCallback(
    async (character: Character) => {
      setSelectedCharacter(character);
      setSelectedCharacterId(character.id);
      setShowWelcome(false);
      try {
        const newConversation = await createConversationMutation.mutateAsync({
          title: `Chat with ${character.name}`,
          mode: "chat",
          characterId: character.id,
        });
        setConversationId(newConversation.id);
        await conversationsQuery.refetch();
        toast.success(t("chat.startedWith", { name: character.name }));
      } catch {
        toast.error(t("chat.failedToStart"));
      }
    },
    [createConversationMutation, conversationsQuery, t]
  );

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || !conversationId) return;
    const userMessage = inputMessage;
    setInputMessage("");
    await sendToConversation(conversationId, userMessage, selectedCharacterId);
  };

  const handleSidebarSend = async () => {
    const draft = sidebarDraft.trim();
    if (!draft) return;
    setSidebarDraft("");
    if (!conversationId) {
      await startGeneralChat(draft);
      return;
    }
    await sendToConversation(conversationId, draft, selectedCharacterId);
  };

  const resetToWelcome = () => {
    setShowWelcome(true);
    setShowSecurity(false);
    setConversationId(null);
    setSelectedCharacter(null);
    setSelectedCharacterId(null);
    setMessages([]);
    localStorage.removeItem(LAST_CONV_KEY);
  };

  const openSecurity = () => {
    setShowSecurity(true);
    setShowWelcome(false);
  };

  const topNav = (
    <header className="h-14 border-b border-border/60 bg-card/80 backdrop-blur flex items-center justify-between px-4 shrink-0">
      <button
        type="button"
        onClick={resetToWelcome}
        className="flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-primary-foreground font-semibold hover:opacity-90 transition-opacity"
      >
        <img src={APP_LOGO_SRC} alt="MonsterAi" className="w-6 h-6 rounded-md object-cover" />
        MonsterAi
      </button>
      <div className="flex items-center gap-2">
        <Button
          variant={showWelcome || conversationId ? "default" : "outline"}
          size="sm"
          className="rounded-full gap-2"
          onClick={() => navigate("/")}
        >
          <MessageSquare className="w-4 h-4" />
          {t("chatPage.messages")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="rounded-full gap-2"
          onClick={() => navigate("/text-to-image")}
        >
          <ImageIcon className="w-4 h-4" />
          {t("chatPage.generateImage")}
        </Button>
        <Button
          variant={showSecurity ? "default" : "outline"}
          size="sm"
          className="rounded-full gap-2 relative"
          onClick={openSecurity}
        >
          <Shield className="w-4 h-4" />
          {t("security.center", "安全中心")}
          <span
            className={`absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full ${
              security.aggregateStatus === "locked"
                ? "bg-red-500"
                : security.aggregateStatus === "warn"
                  ? "bg-amber-500"
                  : "bg-emerald-500"
            }`}
          />
        </Button>
        <LanguageSwitcher />
        <Button variant="ghost" size="icon" className="rounded-full" title={t("common.search", "Search")}>
          <Search className="w-4 h-4" />
        </Button>
        <ThemeSwitcher />
      </div>
    </header>
  );

  const sidebar = (
    <aside className="w-72 border-r border-border/60 bg-[#0a0a0f] flex flex-col shrink-0">
      <div className="p-3">
        <Button
          className="w-full rounded-xl gap-2 bg-primary hover:bg-primary/90"
          onClick={() => void startGeneralChat()}
        >
          <Plus className="w-4 h-4" />
          {t("chatPage.newChat")}
        </Button>
      </div>

      <SecurityStatusBar snapshot={security.snapshot} onOpenSecurity={openSecurity} />

      <div className="px-4 pb-2 flex items-center justify-between">
        <span className="text-sm font-medium text-muted-foreground">{t("chatPage.characters")}</span>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={() => navigate("/characters")}
        >
          <Plus className="w-4 h-4" />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 space-y-1">
        {chatHistory.map((conv) => (
          <button
            key={conv.id}
            type="button"
            onClick={() => resumeConversation(conv)}
            className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors ${
              conversationId === conv.id
                ? "bg-accent/15 text-foreground"
                : "text-muted-foreground hover:bg-muted/40 hover:text-foreground"
            }`}
          >
            <div className="flex items-center gap-2">
              {conv.character ? (
                <CharacterAvatar
                  name={conv.character.name}
                  avatarUrl={conv.character.avatarUrl}
                  size="sm"
                />
              ) : (
                <MessageCircle className="w-7 h-7 text-muted-foreground shrink-0" />
              )}
              <span className="truncate">{conv.character?.name ?? conv.title}</span>
            </div>
          </button>
        ))}
        {allCharacters.slice(0, 6).map((character) => (
          <button
            key={`char-${character.id}`}
            type="button"
            onClick={() => void handleSelectCharacter(character)}
            className="w-full text-left px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-muted/40 hover:text-foreground flex items-center gap-2"
          >
            <CharacterAvatar name={character.name} avatarUrl={character.avatarUrl} size="sm" />
            <span className="truncate">{character.name}</span>
          </button>
        ))}
      </div>

      <CallGuardDownload manifest={security.manifest} compact />

      <div className="p-3 border-t border-border/60">
        <div className="flex gap-2 items-center rounded-xl bg-muted/30 border border-border/50 px-3 py-2">
          <Input
            value={sidebarDraft}
            onChange={(e) => setSidebarDraft(e.target.value)}
            placeholder={t("chatPage.askPlaceholder")}
            className="border-0 bg-transparent shadow-none focus-visible:ring-0 h-8 px-0"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void handleSidebarSend();
              }
            }}
          />
          <Button
            size="icon"
            variant="ghost"
            className="shrink-0 h-8 w-8"
            onClick={() => void handleSidebarSend()}
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </aside>
  );

  const welcomeView = (
    <div className="flex-1 flex flex-col items-center justify-center p-8 overflow-auto">
      <img
        src={APP_LOGO_SRC}
        alt="MonsterAi"
        className="w-24 h-24 rounded-2xl mb-6 shadow-lg shadow-primary/20 object-cover"
      />
      <h1 className="text-4xl font-bold text-foreground mb-3 text-center">
        {t("chatPage.welcomeTitle")}
      </h1>
      <p className="text-muted-foreground mb-10 text-center max-w-lg">
        {t("chatPage.welcomeSubtitle")}
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full max-w-3xl mb-10">
        <Card
          className="p-6 bg-card/60 border-border/60 hover:border-primary/40 cursor-pointer transition-colors"
          onClick={() => navigate("/tutorials")}
        >
          <BookOpen className="w-8 h-8 text-primary mb-3" />
          <h3 className="font-semibold text-foreground">{t("chatPage.learnBasics")}</h3>
        </Card>
        <Card
          className="p-6 bg-card/60 border-border/60 hover:border-primary/40 cursor-pointer transition-colors"
          onClick={() => void startGeneralChat()}
        >
          <MessageCircle className="w-8 h-8 text-primary mb-3" />
          <h3 className="font-semibold text-foreground">{t("chatPage.startChatCard")}</h3>
        </Card>
        <Card
          className="p-6 bg-card/60 border-border/60 hover:border-primary/40 cursor-pointer transition-colors"
          onClick={() => navigate("/characters")}
        >
          <Sparkles className="w-8 h-8 text-primary mb-3" />
          <h3 className="font-semibold text-foreground">{t("chatPage.createCharacter")}</h3>
        </Card>
      </div>

      <Button
        size="lg"
        className="rounded-full px-8 gap-2"
        onClick={() => void startGeneralChat()}
      >
        {t("chatPage.startChattingNow")}
      </Button>

      <div className="w-full max-w-3xl mt-10">
        <CallGuardDownload manifest={security.manifest} />
      </div>
    </div>
  );

  const chatView = (
    <div className="flex-1 flex flex-col overflow-hidden">
      {(selectedCharacter || conversationId) && (
        <div className="border-b border-border/60 px-6 py-3 bg-card/40">
          <h2 className="font-semibold text-foreground">
            {selectedCharacter
              ? t("chat.chatWith", { name: selectedCharacter.name })
              : t("chat.generalChat")}
          </h2>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && selectedCharacter && (
          <div className="flex flex-col items-center justify-center h-full text-center max-w-md mx-auto">
            <CharacterAvatar
              name={selectedCharacter.name}
              avatarUrl={selectedCharacter.avatarUrl}
              size="lg"
              className="mb-4"
            />
            <p className="text-muted-foreground">{selectedCharacter.openingLine}</p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-2xl p-4 rounded-2xl ${
                msg.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-card border border-border/50"
              }`}
            >
              <div className="flex gap-3 items-start">
                {msg.role === "assistant" && selectedCharacter && (
                  <CharacterAvatar
                    name={selectedCharacter.name}
                    avatarUrl={selectedCharacter.avatarUrl}
                    size="sm"
                  />
                )}
                <div className="flex-1 min-w-0">
                  <Streamdown>{msg.content}</Streamdown>
                </div>
                {msg.role === "assistant" && (
                  <button
                    type="button"
                    onClick={() => {
                      if (playingMessageId === msg.id) {
                        stop();
                        setPlayingMessageId(null);
                      } else {
                        speak(msg.content);
                        setPlayingMessageId(msg.id);
                      }
                    }}
                    className="p-1 hover:bg-muted rounded"
                  >
                    {playingMessageId === msg.id && isPlaying ? (
                      <VolumeX className="w-4 h-4" />
                    ) : (
                      <Volume2 className="w-4 h-4" />
                    )}
                  </button>
                )}
                {msg.role === "user" && <User className="w-5 h-5 shrink-0" />}
              </div>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-card border border-border/50 p-4 rounded-2xl flex items-center gap-2">
              <Loader2 className="w-5 h-5 animate-spin text-primary" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-border/60 p-4 bg-card/40">
        <div className="max-w-3xl mx-auto space-y-2">
          <SafeModeToggle
            draft={inputMessage}
            onAnalyze={security.analyzePrompt}
            onTriggerProtection={() => void security.triggerLock("high_risk_prompt")}
            onProceed={() => void handleSendMessage()}
            disabled={isLoading || !conversationId}
          />
          <div className="flex gap-2">
            <Input
              placeholder={t("chat.typeMessage")}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void handleSendMessage();
                }
              }}
              disabled={isLoading || !conversationId || security.snapshot?.crimeguard.network_locked}
              className="rounded-xl"
            />
            <Button
              onClick={() => void handleSendMessage()}
              disabled={isLoading || !inputMessage.trim() || !conversationId}
              className="rounded-xl gap-2"
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );

  if (!canChat) {
    return <SignInPrompt />;
  }

  return (
    <div className="h-screen flex flex-col bg-background text-foreground overflow-hidden">
      {topNav}
      <div className="flex flex-1 min-h-0">
        {sidebar}
        {showSecurity ? (
          <SecurityCenter
            snapshot={security.snapshot}
            manifest={security.manifest}
            reports={security.reports}
            threatCount={security.threatCount}
            locking={security.locking}
            onLock={() => void security.triggerLock()}
            onRecover={(token) => void security.recoverLock(token)}
            onBack={resetToWelcome}
          />
        ) : showWelcome && !conversationId ? (
          welcomeView
        ) : (
          chatView
        )}
      </div>
    </div>
  );
}