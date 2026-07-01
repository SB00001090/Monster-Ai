package ai.monster.callguard.billing

import ai.monster.callguard.BuildConfig
import android.content.Context
import android.content.SharedPreferences
import android.util.Log
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * Local 7-day trial timer — Developed by Suckbob | Monster AI Call Guard
 * No server required; trial starts on first app open.
 */
class TrialManager(context: Context) {
    private val prefs: SharedPreferences = openPrefs(context.applicationContext)

    private fun openPrefs(context: Context): SharedPreferences {
        return try {
            val masterKey = MasterKey.Builder(context)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build()
            EncryptedSharedPreferences.create(
                context,
                "callguard_trial_secure",
                masterKey,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
            )
        } catch (e: Exception) {
            // DOOGEE / MediaTek devices may lack a working Android Keystore TEE.
            Log.w(TAG, "Encrypted prefs unavailable, using fallback store", e)
            context.getSharedPreferences(FALLBACK_PREFS, Context.MODE_PRIVATE)
        }
    }

    fun ensureTrialStarted() {
        if (!prefs.contains(KEY_TRIAL_START)) {
            prefs.edit().putLong(KEY_TRIAL_START, System.currentTimeMillis()).apply()
        }
    }

    fun trialStartMs(): Long = prefs.getLong(KEY_TRIAL_START, System.currentTimeMillis())

    fun trialDays(): Int = BuildConfig.TRIAL_DAYS

    fun trialEndMs(): Long = trialStartMs() + trialDays() * 24L * 60 * 60 * 1000

    fun isTrialActive(): Boolean = System.currentTimeMillis() < trialEndMs()

    fun trialRemainingMs(): Long = (trialEndMs() - System.currentTimeMillis()).coerceAtLeast(0)

    fun setPurchased(permanent: Boolean) {
        prefs.edit().putBoolean(KEY_PURCHASED, permanent).apply()
    }

    fun isPurchased(): Boolean = prefs.getBoolean(KEY_PURCHASED, false)

    /** Trial OR one-time purchase unlocks premium features. */
    fun hasPremiumAccess(): Boolean = isPurchased() || isTrialActive()

    companion object {
        private const val TAG = "TrialManager"
        private const val FALLBACK_PREFS = "callguard_trial_fallback"
        private const val KEY_TRIAL_START = "trial_start_ms"
        private const val KEY_PURCHASED = "purchased_lifetime"
    }
}