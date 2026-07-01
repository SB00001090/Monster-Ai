package ai.monster.callguard.ui.screens

import ai.monster.callguard.antitheft.SimMonitor
import ai.monster.callguard.ui.theme.NeonGreen
import ai.monster.callguard.ui.theme.NeonMagenta
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp

@Composable
fun AntiTheftScreen(
    enabled: Boolean,
    premium: Boolean,
    onToggle: (Boolean) -> Unit,
) {
    val sim = SimMonitor(LocalContext.current).currentState()
    Column(Modifier.padding(20.dp)) {
        Text("防盜模式", style = MaterialTheme.typography.headlineSmall)
        Spacer(Modifier.height(8.dp))
        Text(
            "SIM：${if (sim.simPresent) "已插入" else "未偵測"} · ${sim.carrierName}",
            color = if (sim.simPresent) NeonGreen else NeonMagenta,
        )
        Text("訂閱數：${sim.subscriptionCount}")
        Spacer(Modifier.height(16.dp))
        if (!premium) {
            Text("試用結束後需永久解鎖才能使用防盜進階功能", style = MaterialTheme.typography.bodySmall)
            Spacer(Modifier.height(8.dp))
        }
        Column(Modifier.fillMaxWidth()) {
            Text("啟用背景位置 + SIM 監控")
            Switch(checked = enabled, onCheckedChange = { if (premium) onToggle(it) }, enabled = premium)
        }
        Spacer(Modifier.height(16.dp))
        Text(
            "限制說明：手機關機或無 WiFi/GPS 時無法追蹤。請在設定中授予背景位置權限。",
            style = MaterialTheme.typography.bodySmall,
        )
    }
}