package ai.monster.callguard.antitheft

import ai.monster.callguard.R
import ai.monster.callguard.billing.TrialManager
import ai.monster.callguard.network.HomeMonsterClient
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import androidx.core.app.NotificationCompat
import ai.monster.callguard.ui.MainActivity
import org.json.JSONObject

/**
 * Anti-theft foreground service — SIM change alerts + background location.
 * Developed by Suckbob | Monster Call Guard
 */
class AntiTheftForegroundService : Service() {
    private val handler = Handler(Looper.getMainLooper())
    private lateinit var simMonitor: SimMonitor
    private lateinit var locationTracker: LocationTracker
    private var lastSimFingerprint: String = ""

    private val pollRunnable = object : Runnable {
        override fun run() {
            checkSimChange()
            handler.postDelayed(this, 30_000L)
        }
    }

    override fun onCreate() {
        super.onCreate()
        simMonitor = SimMonitor(this)
        locationTracker = LocationTracker(this, simMonitor)
        lastSimFingerprint = simMonitor.simFingerprint()
        createChannel()
        startForeground(NOTIF_ID, buildNotification("防盜監控運行中"))
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val trial = TrialManager(this)
        if (!trial.hasPremiumAccess()) {
            stopSelf()
            return START_NOT_STICKY
        }
        locationTracker.start { loc ->
            Thread {
                try {
                    val client = HomeMonsterClient(this)
                    val body = JSONObject()
                        .put("lat", loc.latitude)
                        .put("lng", loc.longitude)
                        .put("accuracy", loc.accuracy)
                        .put("sim_present", simMonitor.currentState().simPresent)
                    client.postJson("/api/callguard/antitheft/location", body.toString())
                } catch (_: Exception) {
                }
            }.start()
        }
        handler.removeCallbacks(pollRunnable)
        handler.post(pollRunnable)
        return START_STICKY
    }

    private fun checkSimChange() {
        val fp = simMonitor.simFingerprint()
        if (lastSimFingerprint.isNotEmpty() && fp != lastSimFingerprint) {
            val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            nm.notify(
                NOTIF_ALERT_ID,
                NotificationCompat.Builder(this, CHANNEL_ID)
                    .setSmallIcon(R.drawable.ic_notification)
                    .setContentTitle("SIM 狀態變更偵測")
                    .setContentText("已偵測 SIM 拔除或更換，位置追蹤持續運行（WiFi/GPS）")
                    .setPriority(NotificationCompat.PRIORITY_HIGH)
                    .build(),
            )
            Thread {
                try {
                    val client = HomeMonsterClient(this)
                    val body = JSONObject()
                        .put("event", "sim_change")
                        .put("fingerprint", fp)
                    client.postJson("/api/callguard/antitheft/event", body.toString())
                } catch (_: Exception) {
                }
            }.start()
        }
        lastSimFingerprint = fp
    }

    override fun onDestroy() {
        handler.removeCallbacks(pollRunnable)
        locationTracker.stop()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(CHANNEL_ID, "Anti-Theft", NotificationManager.IMPORTANCE_LOW)
            getSystemService(NotificationManager::class.java).createNotificationChannel(ch)
        }
    }

    private fun buildNotification(text: String): Notification {
        val pi = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle("Monster Call Guard · 防盜")
            .setContentText(text)
            .setContentIntent(pi)
            .setOngoing(true)
            .build()
    }

    companion object {
        private const val CHANNEL_ID = "antitheft"
        private const val NOTIF_ID = 7702
        private const val NOTIF_ALERT_ID = 7703

        fun start(context: Context) {
            val i = Intent(context, AntiTheftForegroundService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(i)
            } else {
                context.startService(i)
            }
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, AntiTheftForegroundService::class.java))
        }
    }
}