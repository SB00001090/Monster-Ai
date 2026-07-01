package ai.monster.callguard.guardian

import ai.monster.callguard.network.ConnectionManager
import android.content.Context
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject

/** Guardian E2E cloud sync — same bundles as Web UI. Developed by Suckbob | Monster Guardian AI */
class GuardianSyncClient(context: Context) {
    private val connection = ConnectionManager.get(context)
    private val client get() = connection.httpClient

    private fun base(): String? = connection.getBaseUrl()

    fun getStatus(): JSONObject? = getJson("/api/guardian/status")

    fun getConnection(): JSONObject? = getJson("/api/guardian/connection")

    fun listBundles(provider: String, providerSub: String): JSONObject? {
        val q =
            "/api/guardian/sync/list?provider=${encode(provider)}&provider_sub=${encode(providerSub)}"
        return getJson(q)
    }

    fun uploadBundle(
        provider: String,
        providerSub: String,
        passphrase: String,
        bundleType: String,
        payload: JSONObject,
        deviceId: String,
    ): JSONObject? {
        val body = JSONObject()
            .put("provider", provider)
            .put("provider_sub", providerSub)
            .put("passphrase", passphrase)
            .put("bundle_type", bundleType)
            .put("payload", payload)
            .put("device_id", deviceId)
        return postJson("/api/guardian/sync/upload", body)
    }

    fun downloadBundle(
        provider: String,
        providerSub: String,
        passphrase: String,
        bundleType: String,
    ): JSONObject? {
        val body = JSONObject()
            .put("provider", provider)
            .put("provider_sub", providerSub)
            .put("passphrase", passphrase)
            .put("bundle_type", bundleType)
        return postJson("/api/guardian/sync/download", body)
    }

    fun exportTrainingVault(): JSONObject? = getJson("/api/guardian/training/export")

    fun importTrainingVault(bundle: JSONObject): JSONObject? =
        postJson("/api/guardian/training/import", bundle)

    private fun getJson(path: String): JSONObject? {
        val base = base() ?: return null
        val req = Request.Builder().url("$base$path").get().build()
        return try {
            client.newCall(req).execute().use { resp ->
                if (!resp.isSuccessful) null
                else JSONObject(resp.body?.string() ?: return null)
            }
        } catch (_: Exception) {
            null
        }
    }

    private fun postJson(path: String, body: JSONObject): JSONObject? {
        val base = base() ?: return null
        val req = Request.Builder()
            .url("$base$path")
            .post(body.toString().toRequestBody("application/json".toMediaType()))
            .build()
        return try {
            client.newCall(req).execute().use { resp ->
                val text = resp.body?.string() ?: return null
                if (!resp.isSuccessful) {
                    return try {
                        JSONObject(text)
                    } catch (_: Exception) {
                        JSONObject().put("ok", false).put("reason", "http_${resp.code}")
                    }
                }
                JSONObject(text)
            }
        } catch (_: Exception) {
            null
        }
    }

    private fun encode(value: String): String =
        java.net.URLEncoder.encode(value, Charsets.UTF_8.name())

    companion object {
        val BUNDLE_TYPES = listOf("preferences", "oc_cards", "chat_sessions", "training_vault")

        fun buildPreferencesPayload(context: Context, tunnelUrl: String?): JSONObject {
            val prefs = context.getSharedPreferences("callguard", Context.MODE_PRIVATE)
            return JSONObject()
                .put("version", 1)
                .put("platform", "android")
                .put("exported_at", java.time.Instant.now().toString())
                .put("tunnel_url", tunnelUrl ?: "")
                .put("antitheft_enabled", prefs.getBoolean("antitheft_enabled", false))
                .put("protection_enabled", prefs.getBoolean("protection_enabled", false))
        }

        fun buildOcPayload(): JSONObject = JSONObject()
            .put("version", 1)
            .put("platform", "android")
            .put("characters", JSONArray())
            .put("note", "Call Guard — OC 文案請於 Web UI 建立後同步")

        fun applyPreferences(context: Context, payload: JSONObject) {
            val prefs = context.getSharedPreferences("callguard", Context.MODE_PRIVATE)
            if (payload.has("antitheft_enabled")) {
                prefs.edit()
                    .putBoolean("antitheft_enabled", payload.optBoolean("antitheft_enabled"))
                    .apply()
            }
            if (payload.has("protection_enabled")) {
                prefs.edit()
                    .putBoolean("protection_enabled", payload.optBoolean("protection_enabled"))
                    .apply()
            }
            val tunnel = payload.optString("tunnel_url", "")
            if (tunnel.startsWith("https://")) {
                ConnectionManager.get(context).saveTunnelUrl(tunnel)
            }
        }
    }
}