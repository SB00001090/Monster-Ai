import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electron', {
  // 版本信息
  getVersion: () => ipcRenderer.invoke('app-version'),

  // 自動更新
  onUpdateAvailable: (callback: () => void) => {
    ipcRenderer.on('update-available', callback);
  },
  onUpdateDownloaded: (callback: () => void) => {
    ipcRenderer.on('update-downloaded', callback);
  },
  restartApp: () => ipcRenderer.send('restart-app'),

  // 離線數據
  getOfflineData: () => ipcRenderer.invoke('get-offline-data'),
  saveOfflineData: (data: any) => ipcRenderer.invoke('save-offline-data', data),

  // 系統信息
  getPlatform: () => process.platform,
  getArch: () => process.arch,

  // Monster Guardian AI — desktop vault passphrase (safeStorage)
  guardianVaultStatus: () => ipcRenderer.invoke('guardian-vault-status'),
  guardianVaultSetPassphrase: (passphrase: string) =>
    ipcRenderer.invoke('guardian-vault-set-passphrase', passphrase),
  guardianVaultGetPassphrase: () => ipcRenderer.invoke('guardian-vault-get-passphrase'),
  guardianVaultClear: () => ipcRenderer.invoke('guardian-vault-clear'),
});

declare global {
  interface Window {
    electron: {
      getVersion: () => Promise<{ version: string }>;
      onUpdateAvailable: (callback: () => void) => void;
      onUpdateDownloaded: (callback: () => void) => void;
      restartApp: () => void;
      getOfflineData: () => Promise<any>;
      saveOfflineData: (data: any) => Promise<boolean>;
      getPlatform: () => string;
      getArch: () => string;
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
