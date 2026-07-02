/** Monster AI Python backend client (7860 / Cloudflare Tunnel). */

const STORAGE_KEY = "monster_api_base";

export function getMonsterApiBase(): string {
  const env = import.meta.env.VITE_MONSTER_API_URL?.trim();
  if (env) return env.replace(/\/$/, "");
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return stored.replace(/\/$/, "");
    // Cloudflare Pages: use same-origin /api/* → Pages Functions → Tunnel
    if (window.location.hostname.includes("pages.dev")) {
      return "";
    }
    if (window.location.port === "5173" || import.meta.env.DEV) {
      return "";
    }
  }
  return "";
}

export function setMonsterApiBase(url: string): void {
  const v = url.trim().replace(/\/$/, "");
  if (v) localStorage.setItem(STORAGE_KEY, v);
  else localStorage.removeItem(STORAGE_KEY);
}

function pagesProxyPath(path: string): string {
  if (typeof window === "undefined") return path;
  if (!window.location.hostname.includes("pages.dev")) return path;
  if (path === "/health") return "/api/health";
  if (path === "/status") return "/api/status";
  return path;
}

function apiUrl(path: string): string {
  const base = getMonsterApiBase();
  const p = pagesProxyPath(path.startsWith("/") ? path : `/${path}`);
  return base ? `${base}${p}` : p;
}

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const r = await fetch(apiUrl(path), {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers as Record<string, string>),
    },
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(text || `HTTP ${r.status}`);
  }
  return r.json() as Promise<T>;
}

export type EcosystemBundle = {
  id: string;
  label: string;
  label_en?: string;
  estimated_minutes?: number;
  step_count?: number;
};

export const monsterApi = {
  health: () => request<{ status: string; version: string }>("/health"),
  status: () => request<Record<string, unknown>>("/status"),

  ecosystemInfo: () =>
    request<{
      product: string;
      developer: string;
      bundles: EcosystemBundle[];
      consent: Record<string, unknown>;
      status: Record<string, unknown>;
    }>("/api/ecosystem/info"),

  ecosystemPrivacy: (locale = "zh-TW") =>
    request<{ locale: string; text: string }>(`/api/ecosystem/privacy?locale=${locale}`),

  ecosystemConsent: (body: { grant: boolean; allow_r18?: boolean; allow_downloads?: boolean }) =>
    request<Record<string, unknown>>("/api/ecosystem/consent", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  ecosystemInstall: (bundle: string) =>
    request<Record<string, unknown>>("/api/ecosystem/install", {
      method: "POST",
      body: JSON.stringify({ bundle }),
    }),

  ecosystemStatus: () =>
    request<Record<string, unknown>>("/api/ecosystem/status"),

  miniInfo: () => request<Record<string, unknown>>("/api/mini/info"),
  miniDisclaimer: (locale = "zh-TW") =>
    request<{ text: string }>(`/api/mini/disclaimer?locale=${locale}`),
  miniSuccess: () => request<Record<string, unknown>>("/api/mini/success"),

  miniGenerate: (body: {
    prompt: string;
    template_id?: string;
    locale?: string;
  }) =>
    request<Record<string, unknown>>("/api/mini/generate", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  miniLikeness: (body: {
    prompt: string;
    reference_id: string;
    template_id?: string;
    locale?: string;
  }) =>
    request<Record<string, unknown>>("/api/mini/generate/likeness", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  miniMultimodal: (body: {
    prompt: string;
    reference_id: string;
    voice_text?: string;
    locale?: string;
  }) =>
    request<Record<string, unknown>>("/api/mini/generate/multimodal", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  integrationsStatus: () =>
    request<Record<string, unknown>>("/api/integrations/status"),

  difyStatus: () => request<Record<string, unknown>>("/api/dify/status"),

  difyWorkflows: () => request<Record<string, unknown>>("/api/dify/workflows"),

  commercialPricing: (region = "GLOBAL") =>
    request<Record<string, unknown>>(`/api/commercial/pricing?region=${region}`),

  commercialTrial: () => request<Record<string, unknown>>("/api/commercial/trial"),

  commercialTrialStart: () =>
    request<Record<string, unknown>>("/api/commercial/trial/start", { method: "POST" }),

  difyGenerate: (body: {
    prompt: string;
    template_id?: string;
    locale?: string;
  }) =>
    request<Record<string, unknown>>("/api/dify/generate", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  async uploadReference(form: FormData) {
    const r = await fetch(apiUrl("/api/mini/reference/upload"), {
      method: "POST",
      body: form,
      credentials: "include",
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },

  guardianStatus: () => request<Record<string, unknown>>("/api/guardian/status"),

  guardianDisclaimer: (locale = "zh-TW") =>
    request<{ text: string; developer: string }>(
      `/api/guardian/disclaimer?locale=${locale}`,
    ),

  guardianConnection: () =>
    request<Record<string, unknown>>("/api/guardian/connection"),

  guardianSyncUpload: (body: {
    provider: "google" | "github";
    provider_sub: string;
    passphrase: string;
    bundle_type: "oc_cards" | "chat_sessions" | "preferences" | "training_vault";
    payload: Record<string, unknown> | unknown[];
    device_id?: string;
  }) =>
    request<Record<string, unknown>>("/api/guardian/sync/upload", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  guardianSyncDownload: (body: {
    provider: "google" | "github";
    provider_sub: string;
    passphrase: string;
    bundle_type: "oc_cards" | "chat_sessions" | "preferences" | "training_vault";
  }) =>
    request<Record<string, unknown>>("/api/guardian/sync/download", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  guardianSyncList: (provider: string, providerSub: string) =>
    request<{
      bundles: Array<{ type: string; uploaded_at: string; device_id?: string }>;
      last_sync: string | null;
      user_hash?: string;
    }>(
      `/api/guardian/sync/list?provider=${encodeURIComponent(provider)}&provider_sub=${encodeURIComponent(providerSub)}`,
    ),

  guardianTrainingExport: () =>
    request<Record<string, unknown>>("/api/guardian/training/export"),

  guardianTrainingImport: (bundle: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/guardian/training/import", {
      method: "POST",
      body: JSON.stringify(bundle),
    }),

  guardianReportError: (body: {
    error_type: string;
    message: string;
    stack?: string;
    context?: string;
    source?: string;
    account_id?: string;
    discord_notify?: boolean;
  }) =>
    request<Record<string, unknown>>("/api/guardian/errors/report", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  guardianManuscriptVersions: (ocId: string) =>
    request<Record<string, unknown>>(`/api/guardian/manuscript/${encodeURIComponent(ocId)}/versions`),

  guardianManuscriptRestore: (ocId: string, version: number) =>
    request<Record<string, unknown>>(`/api/guardian/manuscript/${encodeURIComponent(ocId)}/restore`, {
      method: "POST",
      body: JSON.stringify({ version }),
    }),

  guardianShareCreate: (body: {
    oc_id: string;
    card: Record<string, unknown>;
    owner_id?: string;
    mode: "private" | "link" | "public";
    ttl_hours?: number;
    passphrase: string;
  }) =>
    request<Record<string, unknown>>("/api/guardian/share/create", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  guardianShareImport: (token: string, passphrase: string) =>
    request<Record<string, unknown>>("/api/guardian/share/import", {
      method: "POST",
      body: JSON.stringify({ token, passphrase }),
    }),

  guardianAccountRegister: (username: string, displayName?: string) =>
    request<Record<string, unknown>>("/api/guardian/account/register", {
      method: "POST",
      body: JSON.stringify({ username, display_name: displayName }),
    }),

  guardianAccountLink: (body: {
    account_id: string;
    provider: "google" | "github" | "discord";
    provider_sub: string;
    display_name?: string;
    email?: string;
  }) =>
    request<Record<string, unknown>>("/api/guardian/account/link", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  guardianAccountStatus: (accountId: string) =>
    request<Record<string, unknown>>(
      `/api/guardian/account/status?account_id=${encodeURIComponent(accountId)}`,
    ),

  guardianNetworkLearningStatus: () =>
    request<Record<string, unknown>>("/api/guardian/network-learning/status"),

  guardianNetworkLearningConsent: (body: { consented: boolean; metrics?: boolean }) =>
    request<Record<string, unknown>>("/api/guardian/network-learning/consent", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  guardianNetworkLearningTrigger: (body: { force?: boolean; topics?: string[] | null }) =>
    request<Record<string, unknown>>("/api/guardian/network-learning/trigger", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  guardianNetworkLearningDirectives: (limit = 5) =>
    request<{ directives: Array<Record<string, unknown>> }>(
      `/api/guardian/network-learning/directives?limit=${limit}`,
    ),

  guardianArtTriageStatus: () =>
    request<Record<string, unknown>>("/api/guardian/network-learning/art-triage/status"),

  guardianArtTriageRun: () =>
    request<Record<string, unknown>>("/api/guardian/network-learning/art-triage/run", {
      method: "POST",
      body: JSON.stringify({}),
    }),
};

export function monsterWsUrl(path = "/ws"): string {
  const base = getMonsterApiBase();
  if (base) {
    const u = new URL(base);
    u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
    return `${u.origin}${path}`;
  }
  if (typeof window !== "undefined" && window.location.hostname.includes("pages.dev")) {
    return "";
  }
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${path}`;
}