package ai.monster.callguard.security

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import java.security.MessageDigest

/**
 * Training vault key material — Android Keystore backed.
 * Developed by Suckbob | Monster Guardian AI
 *
 * Passphrase + device-bound salt; never stores plaintext training images.
 */
class TrainingVaultKeyManager(context: Context) {

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

    fun ensureSalt(): String {
        val existing = prefs.getString(KEY_SALT, null)
        if (existing != null) return existing
        val salt = java.util.UUID.randomUUID().toString().replace("-", "")
        prefs.edit().putString(KEY_SALT, salt).apply()
        return salt
    }

    /** Derive key fingerprint for sync — full key stays in Keystore-backed prefs only. */
    fun deriveKeyFingerprint(passphrase: String): String {
        val salt = ensureSalt()
        val material = "guardian-training:$passphrase:$salt"
        val digest = MessageDigest.getInstance("SHA-256").digest(material.toByteArray(Charsets.UTF_8))
        return digest.joinToString("") { "%02x".format(it) }.take(32)
    }

    fun isPassphraseSet(): Boolean = prefs.contains(KEY_PASSPHRASE_HASH)

    fun storePassphraseHash(passphrase: String) {
        val hash = deriveKeyFingerprint(passphrase)
        prefs.edit().putString(KEY_PASSPHRASE_HASH, hash).apply()
    }

    fun verifyPassphrase(passphrase: String): Boolean {
        val stored = prefs.getString(KEY_PASSPHRASE_HASH, null) ?: return false
        return stored == deriveKeyFingerprint(passphrase)
    }

    companion object {
        private const val PREFS_NAME = "monster_guardian_training_vault"
        private const val KEY_SALT = "training_vault_salt"
        private const val KEY_PASSPHRASE_HASH = "training_passphrase_fp"
    }
}