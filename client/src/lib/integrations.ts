/** Third-party integration settings (localStorage). */

export type GenProvider = "monster" | "dify";

const PROVIDER_KEY = "monster_gen_provider";
const DIFY_URL_KEY = "monster_dify_url";
const DIFY_KEY_KEY = "monster_dify_api_key";

export function getGenProvider(): GenProvider {
  if (typeof window === "undefined") return "monster";
  return (localStorage.getItem(PROVIDER_KEY) as GenProvider) || "monster";
}

export function setGenProvider(p: GenProvider): void {
  localStorage.setItem(PROVIDER_KEY, p);
}

export function getDifyConfig(): { url: string; apiKey: string } {
  if (typeof window === "undefined") return { url: "", apiKey: "" };
  return {
    url: localStorage.getItem(DIFY_URL_KEY) || "",
    apiKey: localStorage.getItem(DIFY_KEY_KEY) || "",
  };
}

export function setDifyConfig(url: string, apiKey: string): void {
  localStorage.setItem(DIFY_URL_KEY, url.trim().replace(/\/$/, ""));
  localStorage.setItem(DIFY_KEY_KEY, apiKey.trim());
}