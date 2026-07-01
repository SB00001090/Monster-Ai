import { app, BrowserWindow, ipcMain, Tray, Menu } from 'electron';
import { autoUpdater } from 'electron-updater';
import path from 'path';
import isDev from 'electron-is-dev';
import {
  guardianVaultClear,
  guardianVaultGetPassphrase,
  guardianVaultSetPassphrase,
  guardianVaultStatus,
} from './guardianVault';

let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;

// 離線數據存儲
const offlineDataPath = path.join(app.getPath('userData'), 'offline-data.json');

// 創建主窗口
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.ts'),
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
    },
  });

  const startUrl = isDev
    ? 'http://localhost:5173'
    : `file://${path.join(__dirname, '../dist/index.html')}`;

  mainWindow.loadURL(startUrl);

  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  mainWindow.on('minimize', (event) => {
    event.preventDefault();
    mainWindow?.hide();
  });

  mainWindow.on('close', (event) => {
    if (!app.isQuitting) {
      event.preventDefault();
      mainWindow?.hide();
    }
  });
}

// 創建系統托盤
function createTray() {
  const trayIcon = path.join(__dirname, '../assets/tray-icon.png');
  tray = new Tray(trayIcon);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Show',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      },
    },
    {
      label: 'Hide',
      click: () => {
        if (mainWindow) {
          mainWindow.hide();
        }
      },
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        app.isQuitting = true;
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(contextMenu);

  tray.on('click', () => {
    if (mainWindow?.isVisible()) {
      mainWindow.hide();
    } else {
      mainWindow?.show();
      mainWindow?.focus();
    }
  });
}

// 應用菜單
function createMenu() {
  const template: any[] = [
    {
      label: 'File',
      submenu: [
        {
          label: 'Exit',
          accelerator: 'CmdOrCtrl+Q',
          click: () => {
            app.isQuitting = true;
            app.quit();
          },
        },
      ],
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
      ],
    },
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// 自動更新
function setupAutoUpdater() {
  autoUpdater.checkForUpdatesAndNotify();

  autoUpdater.on('update-available', () => {
    if (mainWindow) {
      mainWindow.webContents.send('update-available');
    }
  });

  autoUpdater.on('update-downloaded', () => {
    if (mainWindow) {
      mainWindow.webContents.send('update-downloaded');
    }
  });
}

// IPC 事件處理
ipcMain.on('app-version', (event) => {
  event.reply('app-version', { version: app.getVersion() });
});

ipcMain.on('restart-app', () => {
  autoUpdater.quitAndInstall();
});

ipcMain.handle('get-offline-data', async () => {
  try {
    const fs = await import('fs').then(m => m.promises);
    const data = await fs.readFile(offlineDataPath, 'utf-8');
    return JSON.parse(data);
  } catch {
    return null;
  }
});

ipcMain.handle('save-offline-data', async (_event, data) => {
  try {
    const fs = await import('fs').then(m => m.promises);
    await fs.writeFile(offlineDataPath, JSON.stringify(data, null, 2));
    return true;
  } catch {
    return false;
  }
});

// Monster Guardian AI — desktop vault key (OS keychain via safeStorage)
ipcMain.handle('guardian-vault-status', async () => guardianVaultStatus());
ipcMain.handle('guardian-vault-set-passphrase', async (_event, passphrase: string) =>
  guardianVaultSetPassphrase(passphrase),
);
ipcMain.handle('guardian-vault-get-passphrase', async () => {
  const p = await guardianVaultGetPassphrase();
  return p ? { ok: true, length: p.length } : { ok: false };
});
ipcMain.handle('guardian-vault-clear', async () => guardianVaultClear());

// 應用事件
app.on('ready', () => {
  createWindow();
  createTray();
  createMenu();
  setupAutoUpdater();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  } else {
    mainWindow.show();
  }
});

// 允許單實例應用
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}
