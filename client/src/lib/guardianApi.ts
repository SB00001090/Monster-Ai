/** Monster Guardian AI client — re-exports from monsterApi. */
import { monsterApi } from "./monsterApi";

export type OAuthProvider = "google" | "github";
export type SyncBundleType = "oc_cards" | "chat_sessions" | "preferences";

export const getGuardianStatus = () => monsterApi.guardianStatus();
export const getGuardianDisclaimer = (locale = "zh-TW") =>
  monsterApi.guardianDisclaimer(locale);
export const getGuardianConnection = () => monsterApi.guardianConnection();

export function uploadGuardianSync(params: {
  provider: OAuthProvider;
  providerSub: string;
  passphrase: string;
  bundleType: SyncBundleType;
  payload: Record<string, unknown> | unknown[];
  deviceId?: string;
}) {
  return monsterApi.guardianSyncUpload({
    provider: params.provider,
    provider_sub: params.providerSub,
    passphrase: params.passphrase,
    bundle_type: params.bundleType,
    payload: params.payload,
    device_id: params.deviceId,
  });
}

export function downloadGuardianSync(params: {
  provider: OAuthProvider;
  providerSub: string;
  passphrase: string;
  bundleType: SyncBundleType;
}) {
  return monsterApi.guardianSyncDownload({
    provider: params.provider,
    provider_sub: params.providerSub,
    passphrase: params.passphrase,
    bundle_type: params.bundleType,
  });
}

export function reportGuardianError(params: {
  errorType: string;
  message: string;
  stack?: string;
  context?: string;
  source?: string;
}) {
  return monsterApi.guardianReportError({
    error_type: params.errorType,
    message: params.message,
    stack: params.stack,
    context: params.context,
    source: params.source,
  });
}