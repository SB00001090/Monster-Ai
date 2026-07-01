export {};

declare global {
  interface Window {
    electron?: {
      getOfflineData: () => Promise<unknown>;
      saveOfflineData: (data: unknown) => Promise<boolean>;
      guardianVaultStatus: () => Promise<{
        configured: boolean;
        safeStorageAvailable: boolean;
        fingerprint?: string;
      }>;
      guardianVaultSetPassphrase: (passphrase: string) => Promise<{
        ok: boolean;
        fingerprint?: string;
        reason?: string;
      }>;
      guardianVaultGetPassphrase: () => Promise<{ ok: boolean; length?: number }>;
      guardianVaultClear: () => Promise<boolean>;
    };
  }
}