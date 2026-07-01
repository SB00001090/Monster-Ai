import { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "@/_core/hooks/useAuth";
import { useGuest } from "@/contexts/GuestContext";
import { useLocation } from "wouter";
import { trpc } from "@/lib/trpc";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import CharacterAvatar from "@/components/CharacterAvatar";
import {
  Loader2,
  Send,
  Plus,
  MessageCircle,
  User,
  Star,
  Volume2,
  VolumeX,
  History,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { Streamdown } from "streamdown";
import { useTranslation } from "react-i18next";
import { useTTS } from "@/hooks/useTTS";
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
  updatedAt?: Date | string;
};

const LAST_CONV_KEY = "monster_last_character_chat";

export default function CharacterChatPage() {
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
  const [isLoading, setIsLoading] = useState(false);
  const [showCharacterSelector, setShowCharacterSelector] = useState(true);
  const [sidebarTab, setSidebarTab] = useState<"history" | "characters">("history");
  const [didAutoResume, setDidAutoResume] = useState(false);
  const [didDeepLink, setDidDeepLink] = useState(false);

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
  const deleteConversationMutation = trpc.chat.deleteConversation.useMutation();

  const resumeConversation = useCallback((conv: ConversationItem) => {
    setConversationId(conv.id);
    setShowCharacterSelector(false);
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
    if (didAutoResume || !conversationsQuery.data?.length) return;
    const deepLinkId = new URLSearchParams(window.location.search).get("character");
    if (deepLinkId) return;
    const chatConvs = conversationsQuery.data.filter(
      (c) => c.mode === "chat"
    ) as ConversationItem[];
    if (chatConvs.length === 0) return;

    const savedId = localStorage.getItem(LAST_CONV_KEY);
    const conv =
      (savedId ? chatConvs.find((c) => c.id === Number(savedId)) : null) ??
      chatConvs[0];

    if (conv) {
      resumeConversation(conv);
      setDidAutoResume(true);
    }
  }, [conversationsQuery.data, didAutoResume, resumeConversation]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSelectCharacter = useCallback(
    async (character: Character) => {
      setSelectedCharacter(character);
      setSelectedCharacterId(character.id);
      setShowCharacterSelector(false);

      try {
        const newConversation = await createConversationMutation.mutateAsync({
          title: `Chat with ${character.name}`,
          mode: "chat",
          characterId: character.id,
        });
        setConversationId(newConversation.id);
        await conversationsQuery.refetch();
        toast.success(t("chat.startedWith", { name: character.name }));
      } catch (error) {
        console.error("Error creating conversation:", error);
        toast.error(t("chat.failedToStart"));
      }
    },
    [createConversationMutation, conversationsQuery, t]
  );

  useEffect(() => {
    if (didDeepLink || !canChat) return;
    const characterId = Number(new URLSearchParams(window.location.search).get("character"));
    if (!characterId || Number.isNaN(characterId)) return;

    const my = myCharactersQuery.data ?? [];
    const pub = publicCharactersQuery.data ?? [];
    const character = [...my, ...pub.filter((pc) => !my.some((mc) => mc.id === pc.id))].find(
      (c) => c.id === characterId
    ) as Character | undefined;
    if (!character) return;

    setDidDeepLink(true);
    setDidAutoResume(true);
    window.history.replaceState({}, "", "/character-chat");
    void handleSelectCharacter(character);
  }, [
    didDeepLink,
    canChat,
    myCharactersQuery.data,
    publicCharactersQuery.data,
    handleSelectCharacter,
  ]);

  const handleDeleteConversation = async (
    convId: number,
    event: React.MouseEvent
  ) => {
    event.stopPropagation();
    if (!confirm(t("chat.deleteConfirm"))) return;

    try {
      await deleteConversationMutation.mutateAsync({ conversationId: convId });
      if (conversationId === convId) {
        setConversationId(null);
        setSelectedCharacter(null);
        setSelectedCharacterId(null);
        setMessages([]);
        localStorage.removeItem(LAST_CONV_KEY);
      }
      await conversationsQuery.refetch();
      toast.success(t("chat.deleted"));
    } catch {
      toast.error(t("chat.deleteFailed"));
    }
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || !conversationId) return;

    const userMessage = inputMessage;
    setInputMessage("");
    setIsLoading(true);

    try {
      const tempUserMessage: Message = {
        id: Date.now(),
        role: "user",
        content: userMessage,
        createdAt: new Date(),
      };
      setMessages((prev) => [...prev, tempUserMessage]);

      const result = await sendMessageMutation.mutateAsync({
        conversationId,
        message: userMessage,
        characterId: selectedCharacterId ?? undefined,
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
    } catch (error) {
      console.error("Error sending message:", error);
      toast.error(t("chat.failedToSend"));
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  };

  const allCharacters = [
    ...(myCharactersQuery.data || []),
    ...(publicCharactersQuery.data || []).filter(
      (pc) => !myCharactersQuery.data?.some((mc) => mc.id === pc.id)
    ),
  ] as Character[];

  const chatHistory = ((conversationsQuery.data ?? []) as ConversationItem[]).filter(
    (c) => c.mode === "chat"
  );

  if (!canChat) {
    return <SignInPrompt />;
  }

  return (
    <div className="flex h-screen bg-background">
      {showCharacterSelector && (
        <div className="w-80 border-r border-border bg-card flex flex-col overflow-hidden">
          <div className="p-4 border-b border-border">
            <h2 className="text-lg font-bold text-foreground">{t("chat.title")}</h2>
            <div className="flex gap-1 mt-3">
              <Button
                size="sm"
                variant={sidebarTab === "history" ? "default" : "ghost"}
                className="flex-1 gap-1"
                onClick={() => setSidebarTab("history")}
              >
                <History className="w-3 h-3" />
                {t("chat.history")}
              </Button>
              <Button
                size="sm"
                variant={sidebarTab === "characters" ? "default" : "ghost"}
                className="flex-1 gap-1"
                onClick={() => setSidebarTab("characters")}
              >
                <Plus className="w-3 h-3" />
                {t("chat.characters")}
              </Button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {sidebarTab === "history" ? (
              chatHistory.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  {t("chat.noHistory")}
                </p>
              ) : (
                chatHistory.map((conv) => (
                  <div
                    key={conv.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => resumeConversation(conv)}
                    onKeyDown={(e) => e.key === "Enter" && resumeConversation(conv)}
                    className={`w-full text-left p-3 rounded-lg border transition-all cursor-pointer ${
                      conversationId === conv.id
                        ? "border-accent bg-accent/10"
                        : "border-border/50 hover:border-accent/50 hover:bg-muted/50"
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      {conv.character ? (
                        <CharacterAvatar
                          name={conv.character.name}
                          avatarUrl={conv.character.avatarUrl}
                          size="sm"
                        />
                      ) : (
                        <MessageCircle className="w-8 h-8 text-muted-foreground" />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate">
                          {conv.character?.name ?? conv.title}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {conv.messageCount ?? 0} {t("chat.messages")}
                        </p>
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-muted-foreground hover:text-destructive"
                        onClick={(e) => handleDeleteConversation(conv.id, e)}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                    {conv.lastMessage && (
                      <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                        {conv.lastMessage}
                      </p>
                    )}
                  </div>
                ))
              )
            ) : allCharacters.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-sm text-muted-foreground mb-4">{t("chat.noCharacters")}</p>
                <Button onClick={() => navigate("/characters")} className="gap-2">
                  <Plus className="w-4 h-4" />
                  {t("chat.createCharacter")}
                </Button>
              </div>
            ) : (
              allCharacters.map((character) => (
                <button
                  key={character.id}
                  onClick={() => handleSelectCharacter(character)}
                  className="w-full text-left p-3 rounded-lg border border-border/50 hover:border-accent/50 hover:bg-muted/50 transition-all"
                >
                  <div className="flex items-start gap-2">
                    <CharacterAvatar
                      name={character.name}
                      avatarUrl={character.avatarUrl}
                      size="sm"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between mb-1">
                        <h3 className="font-semibold text-foreground truncate">
                          {character.name}
                        </h3>
                        {character.averageRating > 0 && (
                          <div className="flex items-center gap-1 flex-shrink-0">
                            <Star className="w-3 h-3 text-yellow-500 fill-yellow-500" />
                            <span className="text-xs font-medium">
                              {character.averageRating}
                            </span>
                          </div>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {character.description}
                      </p>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}

      <div className="flex-1 flex flex-col overflow-hidden">
        {selectedCharacter ? (
          <div className="border-b border-border bg-card p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <CharacterAvatar
                name={selectedCharacter.name}
                avatarUrl={selectedCharacter.avatarUrl}
                size="md"
              />
              <div>
                <h1 className="font-bold text-foreground">{selectedCharacter.name}</h1>
                <p className="text-sm text-muted-foreground line-clamp-1">
                  {selectedCharacter.description}
                </p>
              </div>
            </div>
            <Button
              variant="outline"
              onClick={() => setShowCharacterSelector(true)}
              className="gap-2"
            >
              <History className="w-4 h-4" />
              {t("chat.browse")}
            </Button>
          </div>
        ) : conversationId ? (
          <div className="border-b border-border bg-card p-4 flex items-center justify-between">
            <h1 className="font-bold text-foreground">{t("chat.generalChat")}</h1>
            <Button
              variant="outline"
              onClick={() => setShowCharacterSelector(true)}
              className="gap-2"
            >
              <History className="w-4 h-4" />
              {t("chat.browse")}
            </Button>
          </div>
        ) : null}

        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
          {messages.length === 0 && selectedCharacter && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-md">
                <CharacterAvatar
                  name={selectedCharacter.name}
                  avatarUrl={selectedCharacter.avatarUrl}
                  size="lg"
                  className="mx-auto mb-4"
                />
                <h2 className="text-xl font-bold mb-2 text-foreground">
                  {t("chat.chatWith", { name: selectedCharacter.name })}
                </h2>
                <p className="text-muted-foreground mb-4">
                  {selectedCharacter.openingLine}
                </p>
                <Badge variant="secondary">{selectedCharacter.worldview}</Badge>
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} animate-in fade-in slide-in-from-bottom-2`}
            >
              <div
                className={`max-w-2xl p-4 rounded-lg ${
                  msg.role === "user"
                    ? "bg-accent text-accent-foreground rounded-br-none"
                    : "bg-card text-card-foreground border border-border/50 rounded-bl-none"
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
                  {msg.role === "assistant" && !selectedCharacter && (
                    <MessageCircle className="w-5 h-5 flex-shrink-0 mt-1" />
                  )}
                  <div className="flex-1 min-w-0">
                    <Streamdown>{msg.content}</Streamdown>
                  </div>
                  {msg.role === "assistant" && (
                    <button
                      onClick={() => {
                        if (playingMessageId === msg.id) {
                          stop();
                          setPlayingMessageId(null);
                        } else {
                          speak(msg.content);
                          setPlayingMessageId(msg.id);
                        }
                      }}
                      className="flex-shrink-0 p-1 hover:bg-muted rounded transition-colors"
                      title="Play audio"
                    >
                      {playingMessageId === msg.id && isPlaying ? (
                        <VolumeX className="w-4 h-4" />
                      ) : (
                        <Volume2 className="w-4 h-4" />
                      )}
                    </button>
                  )}
                  {msg.role === "user" && (
                    <User className="w-5 h-5 flex-shrink-0 mt-1" />
                  )}
                </div>
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-card text-card-foreground border border-border/50 p-4 rounded-lg rounded-bl-none flex items-center gap-2">
                {selectedCharacter && (
                  <CharacterAvatar
                    name={selectedCharacter.name}
                    avatarUrl={selectedCharacter.avatarUrl}
                    size="sm"
                  />
                )}
                <Loader2 className="w-5 h-5 animate-spin text-accent" />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {(selectedCharacter || conversationId) && (
          <div className="border-t border-border bg-card p-4 sm:p-6">
            <div className="flex gap-2">
              <Input
                placeholder={t("chat.typeMessage")}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                disabled={isLoading}
                className="flex-1"
              />
              <Button
                onClick={handleSendMessage}
                disabled={isLoading || !inputMessage.trim()}
                className="gap-2 bg-accent hover:bg-accent/90"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}