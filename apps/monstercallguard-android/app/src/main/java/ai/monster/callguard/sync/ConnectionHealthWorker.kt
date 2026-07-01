package ai.monster.callguard.sync

import ai.monster.callguard.network.ConnectionManager
import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters

/** Lightweight background tunnel health probe — battery-friendly interval via WorkManager. */
class ConnectionHealthWorker(appContext: Context, params: WorkerParameters) :
    CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val cm = ConnectionManager.get(applicationContext)
        if (cm.getTunnelUrl() == null) return Result.success()
        return if (cm.probeHealth()) Result.success() else Result.retry()
    }
}