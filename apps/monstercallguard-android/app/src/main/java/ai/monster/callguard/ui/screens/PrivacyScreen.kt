package ai.monster.callguard.ui.screens

import ai.monster.callguard.ui.theme.NeonCyan
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun PrivacyScreen() {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
    ) {
        Text("透明資安告知", style = MaterialTheme.typography.headlineSmall, color = NeonCyan)
        Spacer(Modifier.height(12.dp))
        Text(
            """
            您的資安數據（來電記錄、位置、SIM 狀態、日誌）僅儲存在本機加密空間，並可透過您授權的安全通道同步至您自己的 Monster AI 實例。

            • 只有您與您的 Monster AI 可查看完整數據
            • 開發者 Suckbob 僅在您明確同意後，透過 Monster AI 通道查看匿名化或經同意的數據，用於優化本地模型與防盜規則
            • 無第三方雲端存取 · 無訂閱資料販售
            • 防盜位置追蹤：即使拔出 SIM，在 WiFi/GPS 可用時仍可定位；手機關機則無法追蹤

            Developed by Suckbob | Monster Call Guard
            """.trimIndent(),
            style = MaterialTheme.typography.bodyMedium,
        )
    }
}