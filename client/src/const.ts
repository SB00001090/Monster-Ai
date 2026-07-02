export { COOKIE_NAME, ONE_YEAR_MS } from "@shared/const";

/** Default Monster AI brand mark (served from client/public). */
export const APP_LOGO_SRC = import.meta.env.VITE_APP_LOGO || "/monster-logo.png";

export type OAuthProvider = "google" | "github" | "discord";

export const isOAuthConfigured = () =>
  Boolean(import.meta.env.VITE_OAUTH_PORTAL_URL?.trim());

/** Generate OAuth login URL — optional provider for Google / GitHub buttons. */
export function getOAuthLoginUrl(provider?: OAuthProvider): string {
  const oauthPortalUrl = import.meta.env.VITE_OAUTH_PORTAL_URL?.trim();
  if (!oauthPortalUrl) {
    if (import.meta.env.DEV) {
      const q = provider ? `?provider=${provider}` : "";
      return `/api/oauth/dev-login${q}`;
    }
    return "/login";
  }

  const appId = import.meta.env.VITE_APP_ID;
  const redirectUri = `${window.location.origin}/api/oauth/callback`;
  const state = btoa(redirectUri);

  const url = new URL(`${oauthPortalUrl}/app-auth`);
  url.searchParams.set("appId", appId);
  url.searchParams.set("redirectUri", redirectUri);
  url.searchParams.set("state", state);
  url.searchParams.set("type", "signIn");
  if (provider) {
    url.searchParams.set("provider", provider);
  }

  return url.toString();
}

/** @deprecated Use getOAuthLoginUrl() */
export const getLoginUrl = () => getOAuthLoginUrl();
