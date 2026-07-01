package ai.monster.callguard.antitheft

import android.content.Context
import android.telephony.SubscriptionManager
import android.telephony.TelephonyManager

/**
 * Detects SIM removal / change. Works without premium for alerts;
 * anti-theft tracking requires user-enabled mode + premium after trial.
 */
class SimMonitor(private val context: Context) {
    data class SimState(
        val simPresent: Boolean,
        val subscriptionCount: Int,
        val carrierName: String,
    )

    fun currentState(): SimState {
        val tm = context.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager
        val sm = context.getSystemService(Context.TELEPHONY_SUBSCRIPTION_SERVICE) as SubscriptionManager
        val subs = try {
            sm.activeSubscriptionInfoList?.size ?: 0
        } catch (_: SecurityException) {
            0
        }
        val simPresent = subs > 0 || tm.simState == TelephonyManager.SIM_STATE_READY
        val carrier = try {
            tm.simOperatorName ?: ""
        } catch (_: Exception) {
            ""
        }
        return SimState(simPresent, subs, carrier)
    }

    fun simFingerprint(): String {
        val s = currentState()
        return "${s.subscriptionCount}:${s.carrierName}:${s.simPresent}"
    }
}