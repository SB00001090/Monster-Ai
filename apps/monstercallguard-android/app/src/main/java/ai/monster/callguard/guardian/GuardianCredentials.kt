package ai.monster.callguard.guardian

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * OAuth identity + optional E2E passphrase (Keystore-backed).
 * Developed by Suckbob | Monster Guardian AI
 */
class GuardianCredentials(context: Context) {

    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val prefs = EncryptedSharedPreferences.create(
        context,
        PREFS_NAME,
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    fun getProvider(): String? = prefs.getString(KEY_PROVIDER, null)

    fun getProviderSub(): String? = prefs.getString(KEY_PROVIDER_SUB, null)

    fun isConfigured(): Boolean =
        !getProvider().isNullOrBlank() && !getProviderSub().isNullOrBlank()

    fun saveIdentity(provider: String, providerSub: String) {
        prefs.edit()
            .putString(KEY_PROVIDER, provider.trim().lowercase())
            .putString(KEY_PROVIDER_SUB, providerSub.trim())
            .apply()
    }

    fun savePassphrase(passphrase: String, remember: Boolean) {
        if (remember && passphrase.length >= 8) {
            prefs.edit().putString(KEY_PASSPHRASE, passphrase).apply()
        } else {
            prefs.edit().remove(KEY_PASSPHRASE).apply()
        }
    }

    fun getPassphrase(): String? = prefs.getString(KEY_PASSPHRASE, null)

    fun clearPassphrase() {
        prefs.edit().remove(KEY_PASSPHRASE).apply()
    }

    fun deviceId(context: Context): String {
        val existing = prefs.getString(KEY_DEVICE_ID, null)
        if (existing != null) return existing
        val id = "android_${java.util.UUID.randomUUID().toString().take(12)}"
        prefs.edit().putString(KEY_DEVICE_ID, id).apply()
        return id
    }

    companion object {
        private const val PREFS_NAME = "monster_guardian_sync"
        private const val KEY_PROVIDER = "oauth_provider"
        private const val KEY_PROVIDER_SUB = "oauth_provider_sub"
        private const val KEY_PASSPHRASE = "e2e_passphrase"
        private const val KEY_DEVICE_ID = "guardian_device_id"
    }
}