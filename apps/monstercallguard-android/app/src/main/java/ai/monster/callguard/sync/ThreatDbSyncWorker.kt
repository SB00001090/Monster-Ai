package ai.monster.callguard.sync

import ai.monster.callguard.network.HomeMonsterClient
import ai.monster.callguard.network.ThreatFeedClient
import ai.monster.callguard.security.CredentialBridge
import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters

class ThreatDbSyncWorker(appContext: Context, params: WorkerParameters) :
    CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val homeClient = HomeMonsterClient(applicationContext)
        val feedClient = ThreatFeedClient(applicationContext)
        val token = CredentialBridge.getToken(applicationContext)
        val homeBody = homeClient.fetchThreatDb(token)
        val version = feedClient.fetchAndSaveIfNewer(homeBody)
        return if (version != null || homeBody != null) Result.success() else Result.retry()
    }
}