import { useCallback, useState } from "react";
import { trpc } from "@/lib/trpc";
import {
  downloadGuardianSync,
  exportGuardianTrainingVault,
  importGuardianTrainingVault,
  listGuardianSync,
  uploadGuardianSync,
  type SyncBundleType,
} from "@/lib/guardianApi";
import { getDeviceId } from "@/lib/guardianOAuth";
import type { OAuthProvider } from "@/const";

export type MergeStrategy = "replace" | "merge";

export type SyncBundleMeta = {
  type: string;
  uploaded_at: string;
  device_id?: string;
};

function collectPreferences(): Record<string, unknown> {
  const prefs: Record<string, unknown> = {
    theme: localStorage.getItem("theme"),
    sidebarWidth: localStorage.getItem("sidebar-width"),
    monsterApiBase: localStorage.getItem("monster_api_base"),
    exported_at: new Date().toISOString(),
  };
  try {
    const userInfo = localStorage.getItem("monster-user-info");
    if (userInfo) prefs.user_snapshot = JSON.parse(userInfo);
  } catch {
    /* ignore */
  }
  return prefs;
}

function applyPreferences(payload: Record<string, unknown>) {
  if (typeof payload.theme === "string") {
    localStorage.setItem("theme", payload.theme);
  }
  if (typeof payload.sidebarWidth === "string") {
    localStorage.setItem("sidebar-width", payload.sidebarWidth);
  }
  if (typeof payload.monsterApiBase === "string") {
    localStorage.setItem("monster_api_base", payload.monsterApiBase);
  }
}

export function useGuardianSync() {
  const utils = trpc.useUtils();
  const [busy, setBusy] = useState(false);
  const [bundles, setBundles] = useState<SyncBundleMeta[]>([]);
  const [lastSync, setLastSync] = useState<string | null>(null);

  const refreshManifest = useCallback(
    async (provider: OAuthProvider, providerSub: string) => {
      const data = await listGuardianSync(provider, providerSub);
      setBundles(data.bundles ?? []);
      setLastSync(data.last_sync ?? null);
      return data;
    },
    [],
  );

  const buildPayload = useCallback(
    async (bundleType: SyncBundleType): Promise<Record<string, unknown> | unknown[]> => {
      if (bundleType === "oc_cards") {
        const chars = await utils.client.characters.getMyCharacters.query();
        return {
          version: 1,
          exported_at: new Date().toISOString(),
          characters: chars,
        };
      }
      if (bundleType === "chat_sessions") {
        const convs = await utils.client.chat.getConversations.query();
        const sessions = [];
        for (const conv of convs) {
          const messages = await utils.client.chat.getMessages.query({
            conversationId: conv.id,
          });
          sessions.push({ conversation: conv, messages });
        }
        return {
          version: 1,
          exported_at: new Date().toISOString(),
          sessions,
        };
      }
      if (bundleType === "preferences") {
        return collectPreferences();
      }
      if (bundleType === "training_vault") {
        return exportGuardianTrainingVault();
      }
      return {};
    },
    [utils.client],
  );

  const uploadBundle = useCallback(
    async (params: {
      provider: OAuthProvider;
      providerSub: string;
      passphrase: string;
      bundleType: SyncBundleType;
    }) => {
      setBusy(true);
      try {
        const payload = await buildPayload(params.bundleType);
        const result = await uploadGuardianSync({
          provider: params.provider,
          providerSub: params.providerSub,
          passphrase: params.passphrase,
          bundleType: params.bundleType,
          payload,
          deviceId: getDeviceId(),
        });
        await refreshManifest(params.provider, params.providerSub);
        return result;
      } finally {
        setBusy(false);
      }
    },
    [buildPayload, refreshManifest],
  );

  const downloadBundle = useCallback(
    async (params: {
      provider: OAuthProvider;
      providerSub: string;
      passphrase: string;
      bundleType: SyncBundleType;
    }) => {
      setBusy(true);
      try {
        return await downloadGuardianSync(params);
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  const applyDownloaded = useCallback(
    async (
      bundleType: SyncBundleType,
      payload: unknown,
      strategy: MergeStrategy,
    ): Promise<{ applied: number; skipped: number }> => {
      if (!payload || typeof payload !== "object") {
        return { applied: 0, skipped: 0 };
      }

      const data = payload as Record<string, unknown>;
      let applied = 0;
      let skipped = 0;

      if (bundleType === "preferences") {
        applyPreferences(data);
        return { applied: 1, skipped: 0 };
      }

      if (bundleType === "training_vault") {
        await importGuardianTrainingVault(
          (data.bundle as Record<string, unknown>) ?? data,
        );
        return { applied: 1, skipped: 0 };
      }

      if (bundleType === "oc_cards" && Array.isArray(data.characters)) {
        const existing = await utils.client.characters.getMyCharacters.query();
        const existingNames = new Set(
          existing.map((c: { name: string }) => c.name.toLowerCase()),
        );

        for (const raw of data.characters) {
          const card = raw as {
            name?: string;
            description?: string;
            worldview?: string;
            openingLine?: string;
            systemPrompt?: string | null;
          };
          if (!card.name) {
            skipped += 1;
            continue;
          }
          if (
            strategy === "merge" &&
            existingNames.has(card.name.toLowerCase())
          ) {
            skipped += 1;
            continue;
          }
          await utils.client.characters.create.mutate({
            name: card.name,
            description: card.description ?? "",
            worldview: card.worldview ?? "",
            openingLine: card.openingLine ?? "",
            systemPrompt: card.systemPrompt ?? undefined,
          });
          applied += 1;
        }
        await utils.characters.getMyCharacters.invalidate();
        return { applied, skipped };
      }

      if (bundleType === "chat_sessions" && Array.isArray(data.sessions)) {
        if (strategy === "replace") {
          const local = await utils.client.chat.getConversations.query();
          for (const conv of local) {
            await utils.client.chat.deleteConversation.mutate({
              conversationId: conv.id,
            });
          }
        }

        for (const session of data.sessions) {
          const s = session as {
            conversation?: { title?: string; mode?: "chat" | "image"; characterId?: number };
            messages?: Array<{ role: "user" | "assistant"; content: string }>;
          };
          const conv = await utils.client.chat.createConversation.mutate({
            title: s.conversation?.title ?? "Restored Chat",
            mode: s.conversation?.mode ?? "chat",
            characterId: s.conversation?.characterId,
          });
          for (const msg of s.messages ?? []) {
            if (msg.role === "user" || msg.role === "assistant") {
              await utils.client.chat.addMessage.mutate({
                conversationId: conv.id,
                role: msg.role,
                content: msg.content,
              });
            }
          }
          applied += 1;
        }
        await utils.chat.getConversations.invalidate();
        return { applied, skipped };
      }

      return { applied: 0, skipped: 0 };
    },
    [utils],
  );

  const uploadAll = useCallback(
    async (params: {
      provider: OAuthProvider;
      providerSub: string;
      passphrase: string;
      types: SyncBundleType[];
    }) => {
      const results: Record<string, unknown> = {};
      for (const bundleType of params.types) {
        results[bundleType] = await uploadBundle({
          provider: params.provider,
          providerSub: params.providerSub,
          passphrase: params.passphrase,
          bundleType,
        });
      }
      return results;
    },
    [uploadBundle],
  );

  return {
    busy,
    bundles,
    lastSync,
    refreshManifest,
    uploadBundle,
    uploadAll,
    downloadBundle,
    applyDownloaded,
  };
}