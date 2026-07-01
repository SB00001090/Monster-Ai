package ai.monster.callguard.antitheft

import android.annotation.SuppressLint
import android.content.Context
import android.location.Location
import android.os.Looper
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import ai.monster.callguard.data.AppDatabase
import ai.monster.callguard.data.LocationRecord
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * WiFi + GPS hybrid tracking. Works without SIM if WiFi/GPS available.
 * Limitation: device powered off = no tracking (disclosed in UI).
 */
class LocationTracker(
    private val context: Context,
    private val simMonitor: SimMonitor,
) {
    private val fused = LocationServices.getFusedLocationProviderClient(context)
    private val db = AppDatabase.get(context)
    private var callback: LocationCallback? = null

    @SuppressLint("MissingPermission")
    fun start(onLocation: (Location) -> Unit = {}) {
        stop()
        val request = LocationRequest.Builder(Priority.PRIORITY_BALANCED_POWER_ACCURACY, 60_000L)
            .setMinUpdateIntervalMillis(30_000L)
            .build()
        val cb = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                val loc = result.lastLocation ?: return
                onLocation(loc)
                persist(loc)
            }
        }
        callback = cb
        fused.requestLocationUpdates(request, cb, Looper.getMainLooper())
    }

    fun stop() {
        callback?.let { fused.removeLocationUpdates(it) }
        callback = null
    }

    private fun persist(loc: Location) {
        val sim = simMonitor.currentState()
        val record = LocationRecord(
            latitude = loc.latitude,
            longitude = loc.longitude,
            accuracyM = loc.accuracy,
            source = loc.provider ?: "fused",
            simPresent = sim.simPresent,
            timestampMs = System.currentTimeMillis(),
        )
        CoroutineScope(Dispatchers.IO).launch {
            db.locationDao().insert(record)
        }
    }
}