package ai.monster.callguard.sync

import android.content.Context
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

object SyncScheduler {
    private const val THREAT_SYNC = "callguard_threat_sync"
    private const val HEALTH_PROBE = "callguard_tunnel_health"
    private const val GUARDIAN_SYNC = "guardian_e2e_sync"

    fun schedule(context: Context) {
        val network = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val threat = PeriodicWorkRequestBuilder<ThreatDbSyncWorker>(6, TimeUnit.HOURS)
            .setConstraints(network)
            .build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            THREAT_SYNC,
            ExistingPeriodicWorkPolicy.KEEP,
            threat,
        )
        WorkManager.getInstance(context).enqueue(
            OneTimeWorkRequestBuilder<ThreatDbSyncWorker>().setConstraints(network).build(),
        )

        val health = PeriodicWorkRequestBuilder<ConnectionHealthWorker>(30, TimeUnit.MINUTES)
            .setConstraints(network)
            .build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            HEALTH_PROBE,
            ExistingPeriodicWorkPolicy.KEEP,
            health,
        )

        val guardian = PeriodicWorkRequestBuilder<GuardianSyncWorker>(12, TimeUnit.HOURS)
            .setConstraints(network)
            .build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            GUARDIAN_SYNC,
            ExistingPeriodicWorkPolicy.KEEP,
            guardian,
        )
    }
}