package ai.monster.callguard.ui.screens

import ai.monster.callguard.guardian.GuardianCredentials
import ai.monster.callguard.guardian.GuardianSyncClient
import ai.monster.callguard.network.ConnectionManager
import ai.monster.callguard.ui.theme.NeonCyan
import ai.monster.callguard.ui.theme.NeonGreen
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

/** Monster Guardian AI E2E sync — Android ↔ Web. Developed by Suckbob | Monster Guardian AI */
@Composable
fun GuardianSyncScreen(
    onBack: () -> Unit,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val creds = remember { GuardianCredentials(context) }
    val client = remember { GuardianSyncClient(context) }

    var provider by remember { mutableStateOf(creds.getProvider() ?: "google") }
    var providerSub by remember { mutableStateOf(creds.getProviderSub() ?: "") }
    var passphrase by remember { mutableStateOf(creds.getPassphrase() ?: "") }
    var rememberPass by remember { mutableStateOf(creds.getPassphrase() != null) }
    var status by remember { mutableStateOf("輸入 Google/GitHub 帳戶 sub 與 E2E passphrase（≥8 字）") }
    var manifest by remember { mutableStateOf("") }
    var selectedBundles by remember {
        mutableStateOf(setOf("preferences", "oc_cards"))
    }

    fun refreshManifest() {
        scope.launch {
            status = "讀取 manifest…"
            val data = withContext(Dispatchers.IO) {
                client.listBundles(provider, providerSub)
            }
            manifest = if (data == null) {
                "無法連線或尚未上傳"
            } else {
                val bundles = data.optJSONArray("bundles")
                buildString {
                    append("last_sync: ${data.optString("last_sync", "—")}\n")
                    if (bundles != null) {
                        for (i in 0 until bundles.length()) {
                            val b = bundles.getJSONObject(i)
                            append("• ${b.optString("type")} @ ${b.optString("uploaded_at")}\n")
                        }
                    }
                }
            }
            status = "Manifest 已更新"
        }
    }

    Column(
        Modifier
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
    ) {
        Text("◢ Monster Guardian 同步 ◤", style = MaterialTheme.typography.headlineSmall, color = NeonCyan)
        Text("Developed by Suckbob | Monster Guardian AI", style = MaterialTheme.typography.labelSmall)
        Text("端到端加密 · 與 Web /guardian-sync 互通", color = NeonGreen, style = MaterialTheme.typography.labelMedium)
        Spacer(Modifier.height(12.dp))
        Text(status, style = MaterialTheme.typography.bodySmall)
        Spacer(Modifier.height(12.dp))

        OutlinedTextField(
            provider,
            { provider = it },
            label = { Text("OAuth Provider (google / github)") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(
            providerSub,
            { providerSub = it },
            label = { Text("Provider Sub (Web 登入後 openId)") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        Text(
            "於 Web 設定頁查看帳號；dev 模式：dev_google_user / dev_github_user",
            style = MaterialTheme.typography.labelSmall,
            color = Color.Gray,
        )
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(
            passphrase,
            { passphrase = it },
            label = { Text("E2E Passphrase") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        androidx.compose.foundation.layout.Row(
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Checkbox(rememberPass, { rememberPass = it })
            Text("記住 passphrase（Keystore 加密）", style = MaterialTheme.typography.labelSmall)
        }

        Spacer(Modifier.height(8.dp))
        GuardianSyncClient.BUNDLE_TYPES.forEach { type ->
            val checked = selectedBundles.contains(type)
            androidx.compose.foundation.layout.Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(checked, {
                    selectedBundles = if (it) selectedBundles + type else selectedBundles - type
                })
                Text(type, style = MaterialTheme.typography.bodySmall)
            }
        }

        Spacer(Modifier.height(12.dp))
        Button(
            onClick = {
                creds.saveIdentity(provider, providerSub)
                creds.savePassphrase(passphrase, rememberPass)
                refreshManifest()
            },
            modifier = Modifier.fillMaxWidth(),
        ) { Text("儲存身份並刷新 Manifest") }

        Button(
            onClick = {
                scope.launch {
                    if (passphrase.length < 8) {
                        status = "Passphrase 至少 8 字"
                        return@launch
                    }
                    creds.saveIdentity(provider, providerSub)
                    creds.savePassphrase(passphrase, rememberPass)
                    status = "加密上傳中…"
                    var ok = 0
                    for (bundleType in selectedBundles) {
                        val payload = withContext(Dispatchers.IO) {
                            when (bundleType) {
                                "preferences" -> GuardianSyncClient.buildPreferencesPayload(
                                    context,
                                    ConnectionManager.get(context).getTunnelUrl(),
                                )
                                "oc_cards" -> GuardianSyncClient.buildOcPayload()
                                "chat_sessions" -> JSONObject()
                                    .put("version", 1)
                                    .put("platform", "android")
                                    .put("sessions", org.json.JSONArray())
                                "training_vault" -> client.exportTrainingVault() ?: JSONObject()
                                else -> JSONObject()
                            }
                        }
                        val result = withContext(Dispatchers.IO) {
                            client.uploadBundle(
                                provider = provider,
                                providerSub = providerSub,
                                passphrase = passphrase,
                                bundleType = bundleType,
                                payload = payload,
                                deviceId = creds.deviceId(context),
                            )
                        }
                        if (result?.optBoolean("ok") == true) ok++
                    }
                    status = "已上傳 $ok / ${selectedBundles.size} bundle"
                    refreshManifest()
                }
            },
            modifier = Modifier.fillMaxWidth(),
        ) { Text("加密上傳") }

        Button(
            onClick = {
                scope.launch {
                    if (passphrase.length < 8) {
                        status = "Passphrase 至少 8 字"
                        return@launch
                    }
                    status = "下載 preferences…"
                    val result = withContext(Dispatchers.IO) {
                        client.downloadBundle(provider, providerSub, passphrase, "preferences")
                    }
                    if (result?.optBoolean("ok") != true) {
                        status = "下載失敗：${result?.optString("reason", "unknown")}"
                        return@launch
                    }
                    val payload = result.opt("payload")
                    if (payload is JSONObject) {
                        GuardianSyncClient.applyPreferences(context, payload)
                        status = "已還原 preferences（含 Tunnel URL）"
                    } else {
                        status = "payload 格式錯誤"
                    }
                }
            },
            modifier = Modifier.fillMaxWidth(),
        ) { Text("下載並還原 Preferences") }

        Spacer(Modifier.height(8.dp))
        Text(manifest, style = MaterialTheme.typography.labelSmall, fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace)
        Spacer(Modifier.height(12.dp))
        Button(onClick = onBack, modifier = Modifier.fillMaxWidth()) { Text("返回") }
    }
}