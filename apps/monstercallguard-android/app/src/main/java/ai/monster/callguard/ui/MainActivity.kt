package ai.monster.callguard.ui

import ai.monster.callguard.antitheft.AntiTheftForegroundService
import ai.monster.callguard.billing.BillingManager
import ai.monster.callguard.billing.TrialManager
import ai.monster.callguard.network.ConnectionManager
import ai.monster.callguard.network.ConnectionMode
import ai.monster.callguard.network.ConnectionState
import ai.monster.callguard.network.HomeMonsterClient
import ai.monster.callguard.network.TunnelConnection
import ai.monster.callguard.service.CallGuardForegroundService
import ai.monster.callguard.sync.SyncScheduler
import ai.monster.callguard.ui.screens.AntiTheftScreen
import ai.monster.callguard.ui.screens.HomeScreen
import ai.monster.callguard.ui.screens.PaywallScreen
import ai.monster.callguard.ui.screens.PrivacyScreen
import ai.monster.callguard.ui.theme.MonsterCallGuardTheme
import android.Manifest
import android.app.role.RoleManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import kotlinx.coroutines.launch
import java.io.File
import java.util.concurrent.TimeUnit

/** Developed by Suckbob | Monster AI Call Guard */
class MainActivity : ComponentActivity() {
    private lateinit var trialManager: TrialManager
    private lateinit var billingManager: BillingManager
    private val prefs by lazy { getSharedPreferences("callguard", Context.MODE_PRIVATE) }
    private val connectionManager by lazy { ConnectionManager.get(this) }

    private var statusText by mutableStateOf("")
    private var trialLabel by mutableStateOf("")
    private var tunnelUrl by mutableStateOf("")
    private var antiTheftEnabled by mutableStateOf(false)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        trialManager = TrialManager(this)
        trialManager.ensureTrialStarted()
        billingManager = BillingManager(this, trialManager) { refreshTrialLabel() }
        billingManager.start()

        tunnelUrl = TunnelConnection.loadSaved(this).orEmpty()
        antiTheftEnabled = prefs.getBoolean("antitheft_enabled", false)
        statusText = readCrashLog().ifBlank { TunnelConnection.setupHint() }
        refreshTrialLabel()
        requestRuntimePermissions()
        SyncScheduler.schedule(this)

        lifecycleScope.launch { connectionManager.probeHealth() }

        setContent {
            MonsterCallGuardTheme {
                val nav = rememberNavController()
                val connState by connectionManager.state.collectAsState()
                val connMode by connectionManager.mode.collectAsState()
                Scaffold { pad ->
                    NavHost(nav, "home", Modifier.padding(pad)) {
                        composable("home") {
                            HomeScreen(
                                statusText = statusText,
                                tunnelUrl = tunnelUrl,
                                connectionState = connState,
                                connectionMode = connMode,
                                trialLabel = trialLabel,
                                onTunnelChange = { tunnelUrl = it },
                                onSave = { saveTunnel() },
                                onTest = { testConnection() },
                                onEnableScreening = { requestCallScreeningRole() },
                                onStartProtection = { startProtection() },
                                onNavPaywall = { nav.navigate("paywall") },
                                onNavPrivacy = { nav.navigate("privacy") },
                                onNavAntiTheft = { nav.navigate("antitheft") },
                            )
                        }
                        composable("paywall") {
                            PaywallScreen(
                                trialManager = trialManager,
                                billingManager = billingManager,
                                onPurchase = { billingManager.launchPurchase(this@MainActivity) },
                                onRestore = { billingManager.restorePurchases() },
                            )
                        }
                        composable("privacy") { PrivacyScreen() }
                        composable("antitheft") {
                            AntiTheftScreen(
                                enabled = antiTheftEnabled,
                                premium = trialManager.hasPremiumAccess(),
                                onToggle = { on -> setAntiTheft(on) },
                            )
                        }
                    }
                }
            }
        }
    }

    override fun onDestroy() {
        billingManager.destroy()
        super.onDestroy()
    }

    private fun refreshTrialLabel() {
        trialLabel = when {
            trialManager.isPurchased() -> "已永久解鎖 ✓"
            trialManager.isTrialActive() -> {
                val ms = trialManager.trialRemainingMs()
                val d = TimeUnit.MILLISECONDS.toDays(ms)
                val h = TimeUnit.MILLISECONDS.toHours(ms) % 24
                "試用中 · 剩餘 ${d}天${h}時"
            }
            else -> "試用已結束 · 請永久解鎖"
        }
    }

    private fun saveTunnel() {
        val err = TunnelConnection.validateOrError(tunnelUrl)
        if (err != null) {
            statusText = err
            Toast.makeText(this, err, Toast.LENGTH_LONG).show()
            return
        }
        val saved = connectionManager.saveTunnelUrl(tunnelUrl)
        if (saved == null) {
            Toast.makeText(this, "無效 URL", Toast.LENGTH_SHORT).show()
            return
        }
        tunnelUrl = saved
        Toast.makeText(this, "已儲存 Tunnel URL", Toast.LENGTH_SHORT).show()
        lifecycleScope.launch {
            statusText = HomeMonsterClient(this@MainActivity).testConnection()
        }
    }

    private fun testConnection() {
        lifecycleScope.launch {
            statusText = "測試連線中…"
            statusText = HomeMonsterClient(this@MainActivity).testConnection()
        }
    }

    private fun startProtection() {
        val hasUsb = connectionManager.mode.value == ConnectionMode.USB_LOCAL ||
            connectionManager.getBaseUrl()?.startsWith("http://127.0.0.1") == true
        val hasTunnel = connectionManager.getTunnelUrl() != null
        if (!hasUsb && !hasTunnel) {
            Toast.makeText(this, "請 USB 連接電腦或設定 Tunnel URL", Toast.LENGTH_LONG).show()
            return
        }
        prefs.edit().putBoolean("protection_enabled", true).apply()
        CallGuardForegroundService.start(this)
        Toast.makeText(this, "背景保護已啟動", Toast.LENGTH_SHORT).show()
    }

    private fun setAntiTheft(on: Boolean) {
        antiTheftEnabled = on
        prefs.edit().putBoolean("antitheft_enabled", on).apply()
        if (on && trialManager.hasPremiumAccess()) {
            requestAntiTheftPermissions()
            AntiTheftForegroundService.start(this)
        } else {
            AntiTheftForegroundService.stop(this)
        }
    }

    private fun requestCallScreeningRole() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val rm = getSystemService(RoleManager::class.java)
            if (rm.isRoleAvailable(RoleManager.ROLE_CALL_SCREENING)) {
                startActivityForResult(rm.createRequestRoleIntent(RoleManager.ROLE_CALL_SCREENING), 42)
            }
        }
    }

    private fun requestRuntimePermissions() {
        val perms = mutableListOf(
            Manifest.permission.READ_PHONE_STATE,
            Manifest.permission.READ_CALL_LOG,
        )
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            perms.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            perms.add(Manifest.permission.BLUETOOTH_CONNECT)
        }
        ActivityCompat.requestPermissions(
            this,
            perms.filter {
                ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
            }.toTypedArray(),
            1,
        )
        val pm = getSystemService(POWER_SERVICE) as PowerManager
        if (!pm.isIgnoringBatteryOptimizations(packageName)) {
            try {
                startActivity(
                    Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
                        .setData(Uri.parse("package:$packageName")),
                )
            } catch (_: Exception) {
            }
        }
    }

    private fun requestAntiTheftPermissions() {
        val perms = mutableListOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
        )
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            perms.add(Manifest.permission.ACCESS_BACKGROUND_LOCATION)
        }
        ActivityCompat.requestPermissions(
            this,
            perms.filter {
                ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
            }.toTypedArray(),
            2,
        )
    }

    private fun readCrashLog(): String {
        val f = File(filesDir, "last_crash.txt")
        return if (f.exists()) f.readText().take(500) else ""
    }
}