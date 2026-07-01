package ai.monster.callguard.ui.screens

import ai.monster.callguard.billing.BillingManager
import ai.monster.callguard.billing.TrialManager
import ai.monster.callguard.ui.theme.NeonCyan
import ai.monster.callguard.ui.theme.NeonGreen
import ai.monster.callguard.ui.theme.NeonMagenta
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import java.util.concurrent.TimeUnit

@Composable
fun PaywallScreen(
    trialManager: TrialManager,
    billingManager: BillingManager,
    onPurchase: () -> Unit,
    onRestore: () -> Unit,
) {
    val remaining = trialManager.trialRemainingMs()
    val days = TimeUnit.MILLISECONDS.toDays(remaining)
    val hours = TimeUnit.MILLISECONDS.toHours(remaining) % 24

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text("◢◤ MONSTER CALL GUARD", style = MaterialTheme.typography.headlineSmall, color = NeonCyan)
        Spacer(Modifier.height(12.dp))
        if (trialManager.isTrialActive()) {
            Text(
                "試用剩餘：${days} 天 ${hours} 小時",
                color = NeonGreen,
                fontWeight = FontWeight.Bold,
            )
            Text("試用期間所有功能已解鎖", style = MaterialTheme.typography.bodyMedium)
        } else {
            Text("試用已結束", color = NeonMagenta, fontWeight = FontWeight.Bold)
            Text("一次付費，永久使用 — 無訂閱", style = MaterialTheme.typography.bodyLarge)
        }
        Spacer(Modifier.height(24.dp))
        Text(
            "本地價格：${billingManager.formattedPrice()}",
            style = MaterialTheme.typography.titleMedium,
        )
        Text(
            "Google Play 會依您所在地區顯示合理定價",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
        )
        Spacer(Modifier.height(32.dp))
        Button(
            onClick = onPurchase,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = NeonCyan),
        ) {
            Text("永久解鎖", color = MaterialTheme.colorScheme.background, fontWeight = FontWeight.Bold)
        }
        Spacer(Modifier.height(12.dp))
        OutlinedButton(onClick = onRestore, modifier = Modifier.fillMaxWidth()) {
            Text("恢復購買")
        }
        Spacer(Modifier.height(24.dp))
        Text(
            "Developed by Suckbob | Monster AI Ecosystem",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
        )
    }
}