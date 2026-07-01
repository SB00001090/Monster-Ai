package ai.monster.callguard.sync

import ai.monster.callguard.guardian.GuardianCredentials
import ai.monster.callguard.guardian.GuardianSyncClient
import ai.monster.callguard.network.ConnectionManager
import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Background Guardian preferences sync when E2E passphrase is remembered.
 * Developed by Suckbob | Monster Guardian AI
 */
class GuardianSyncWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val creds = GuardianCredentials(applicationContext)
        if (!creds.isConfigured()) return@withContext Result.success()

        val passphrase = creds.getPassphrase()
        if (passphrase.isNullOrBlank() || passphrase.length < 8) {
            return@withContext Result.success()
        }

        val provider = creds.getProvider() ?: return@withContext Result.success()
        val sub = creds.getProviderSub() ?: return@withContext Result.success()
        val client = GuardianSyncClient(applicationContext)
        val tunnel = ConnectionManager.get(applicationContext).getTunnelUrl()
        val payload = GuardianSyncClient.buildPreferencesPayload(applicationContext, tunnel)

        val result = client.uploadBundle(
            provider = provider,
            providerSub = sub,
            passphrase = passphrase,
            bundleType = "preferences",
            payload = payload,
            deviceId = creds.deviceId(applicationContext),
        )

        if (result?.optBoolean("ok") == true) Result.success()
        else Result.retry()
    }
}