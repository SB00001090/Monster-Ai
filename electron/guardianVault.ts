/**
 * Monster Guardian AI — desktop training vault passphrase store.
 * Developed by Suckbob | Monster Guardian AI
 *
 * Passphrase encrypted at rest via Electron safeStorage (OS keychain).
 */
import { app, safeStorage } from "electron";
import crypto from "crypto";
import fs from "fs/promises";
import path from "path";

const VAULT_FILE = "guardian-vault.enc";

function vaultPath(): string {
  return path.join(app.getPath("userData"), VAULT_FILE);
}

function fingerprint(passphrase: string, salt: string): string {
  return crypto
    .createHash("sha256")
    .update(`monster-guardian-desktop:${salt}:${passphrase}`, "utf8")
    .digest("hex")
    .slice(0, 32);
}

export async function guardianVaultStatus(): Promise<{
  configured: boolean;
  safeStorageAvailable: boolean;
  fingerprint?: string;
}> {
  try {
    const raw = await fs.readFile(vaultPath(), "utf8");
    const meta = JSON.parse(raw) as { salt: string; fp: string };
    return {
      configured: true,
      safeStorageAvailable: safeStorage.isEncryptionAvailable(),
      fingerprint: meta.fp,
    };
  } catch {
    return {
      configured: false,
      safeStorageAvailable: safeStorage.isEncryptionAvailable(),
    };
  }
}

export async function guardianVaultSetPassphrase(
  passphrase: string,
): Promise<{ ok: boolean; fingerprint?: string; reason?: string }> {
  if (passphrase.length < 8) {
    return { ok: false, reason: "passphrase_too_short" };
  }
  if (!safeStorage.isEncryptionAvailable()) {
    return { ok: false, reason: "safe_storage_unavailable" };
  }
  const salt = crypto.randomBytes(16).toString("hex");
  const fp = fingerprint(passphrase, salt);
  const encrypted = safeStorage.encryptString(passphrase).toString("base64");
  await fs.writeFile(
    vaultPath(),
    JSON.stringify({ salt, fp, encrypted, updated_at: new Date().toISOString() }),
    "utf8",
  );
  return { ok: true, fingerprint: fp };
}

export async function guardianVaultGetPassphrase(): Promise<string | null> {
  if (!safeStorage.isEncryptionAvailable()) return null;
  try {
    const raw = await fs.readFile(vaultPath(), "utf8");
    const meta = JSON.parse(raw) as { encrypted: string };
    const buf = Buffer.from(meta.encrypted, "base64");
    return safeStorage.decryptString(buf);
  } catch {
    return null;
  }
}

export async function guardianVaultClear(): Promise<boolean> {
  try {
    await fs.unlink(vaultPath());
    return true;
  } catch {
    return false;
  }
}