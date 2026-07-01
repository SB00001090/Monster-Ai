package ai.monster.callguard.ui.screens

import ai.monster.callguard.ProtectionState
import ai.monster.callguard.network.ConnectionMode
import ai.monster.callguard.network.ConnectionState
import ai.monster.callguard.ui.theme.NeonCyan
import ai.monster.callguard.ui.theme.NeonGreen
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

@Composable
fun HomeScreen(
    statusText: String,
    tunnelUrl: String,
    connectionState: ConnectionState,
    connectionMode: ConnectionMode,
    trialLabel: String,
    onTunnelChange: (String) -> Unit,
    onSave: () -> Unit,
    onTest: () -> Unit,
    onEnableScreening: () -> Unit,
    onStartProtection: () -> Unit,
    onNavPaywall: () -> Unit,
    onNavPrivacy: () -> Unit,
    onNavAntiTheft: () -> Unit,
    onNavGuardianSync: () -> Unit,
) {
    var tunnel by remember(tunnelUrl) { mutableStateOf(tunnelUrl) }

    val modeLabel = when (connectionMode) {
        ConnectionMode.USB_LOCAL -> "USB 本機"
        ConnectionMode.TUNNEL_REMOTE -> "Tunnel 遠端"
        ConnectionMode.NONE -> "未選擇"
    }
    val stateLabel = when (connectionState) {
        ConnectionState.CONNECTED -> "已連線 · $modeLabel"
        ConnectionState.CONNECTING -> "連線中…"
        ConnectionState.DEGRADED -> "離線模式 · 使用快取"
        ConnectionState.OFFLINE -> "未連線"
        ConnectionState.NOT_CONFIGURED -> "USB 或 Tunnel URL"
    }
    val stateColor = when (connectionState) {
        ConnectionState.CONNECTED -> NeonGreen
        ConnectionState.DEGRADED -> Color(0xFFFFB020)
        ConnectionState.CONNECTING -> NeonCyan
        else -> Color(0xFFFF6B6B)
    }

    Column(Modifier.padding(16.dp)) {
        Text("◢ Monster Call Guard ◤", style = MaterialTheme.typography.headlineSmall, color = NeonCyan)
        Text("Developed by Suckbob | Monster AI", style = MaterialTheme.typography.labelSmall)
        Text(trialLabel, color = NeonGreen, style = MaterialTheme.typography.labelLarge)
        Spacer(Modifier.height(8.dp))
        Text("今日攔截：${ProtectionState.rejectsToday.get()} · 鎖網：${ProtectionState.networkLocked.get()}")
        Spacer(Modifier.height(4.dp))
        Text(stateLabel, color = stateColor, style = MaterialTheme.typography.labelMedium)
        Spacer(Modifier.height(8.dp))
        Text(statusText, style = MaterialTheme.typography.bodySmall)
        Spacer(Modifier.height(16.dp))
        OutlinedTextField(
            tunnel,
            { tunnel = it; onTunnelChange(it) },
            label = { Text("Cloudflare Tunnel URL") },
            placeholder = { Text("https://xxx.trycloudflare.com") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        Text(
            "USB：電腦執行 install-apk-adb.bat（唔使 IP）\n遠端：貼 run-tunnel.bat 嘅 HTTPS 網址",
            style = MaterialTheme.typography.labelSmall,
            modifier = Modifier.padding(top = 4.dp),
        )
        Spacer(Modifier.height(8.dp))
        Button(onClick = onSave, modifier = Modifier.fillMaxWidth()) { Text("儲存 Tunnel URL") }
        Button(onClick = onTest, modifier = Modifier.fillMaxWidth()) { Text("測試連線") }
        Button(onClick = onEnableScreening, modifier = Modifier.fillMaxWidth()) { Text("設為來電過濾 App") }
        Button(onClick = onStartProtection, modifier = Modifier.fillMaxWidth()) { Text("啟動背景保護") }
        Spacer(Modifier.height(8.dp))
        Button(onClick = onNavPaywall, modifier = Modifier.fillMaxWidth()) { Text("付費 / 試用") }
        Button(onClick = onNavPrivacy, modifier = Modifier.fillMaxWidth()) { Text("透明資安告知") }
        Button(onClick = onNavAntiTheft, modifier = Modifier.fillMaxWidth()) { Text("防盜模式") }
        Button(onClick = onNavGuardianSync, modifier = Modifier.fillMaxWidth()) {
            Text("Monster Guardian 雲端同步")
        }
    }
}