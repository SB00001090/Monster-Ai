import type { OAuthProvider } from "@/const";

export function resolveOAuthProvider(loginMethod?: string | null): OAuthProvider | null {
  const m = (loginMethod || "").toLowerCase();
  if (m.includes("google")) return "google";
  if (m.includes("github")) return "github";
  return null;
}

export function getDeviceId(): string {
  const key = "guardian-device-id";
  if (typeof window === "undefined") return "web";
  let id = localStorage.getItem(key);
  if (!id) {
    id = `web_${crypto.randomUUID().slice(0, 12)}`;
    localStorage.setItem(key, id);
  }
  return id;
}