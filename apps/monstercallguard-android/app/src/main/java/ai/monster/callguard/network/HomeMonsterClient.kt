package ai.monster.callguard.network

import android.content.Context
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

/** Retrofit/OkHttp client — Cloudflare Tunnel HTTPS only. Developed by Suckbob | Monster AI */
class HomeMonsterClient(context: Context) {
    private val connection = ConnectionManager.get(context)
    private val client get() = connection.httpClient

    fun getBaseUrl(): String? = connection.getBaseUrl()

    fun connectionState(): ConnectionState = connection.state.value

    fun connectionMode(): ConnectionMode = connection.mode.value

    fun testConnection(): String = connection.testConnectionMessage()

    fun analyzeRemote(number: String, displayName: String, token: String?): JSONObject? {
        val base = getBaseUrl() ?: return null
        val body = JSONObject()
            .put("number", number)
            .put("display_name", displayName)
            .put("deep", true)
            .toString()
            .toRequestBody("application/json".toMediaType())
        val req = Request.Builder()
            .url("$base/api/callguard/analyze")
            .post(body)
            .apply { if (token != null) header("Authorization", "Bearer $token") }
            .build()
        return try {
            client.newCall(req).execute().use { resp ->
                if (!resp.isSuccessful) null else JSONObject(resp.body?.string() ?: return null)
            }
        } catch (_: Exception) {
            null
        }
    }

    fun submitReport(payload: JSONObject, token: String?): Boolean {
        val base = getBaseUrl() ?: return false
        val req = Request.Builder()
            .url("$base/api/callguard/report")
            .post(payload.toString().toRequestBody("application/json".toMediaType()))
            .apply { if (token != null) header("Authorization", "Bearer $token") }
            .build()
        return try {
            client.newCall(req).execute().use { it.isSuccessful }
        } catch (_: Exception) {
            false
        }
    }

    fun fetchToken(): String? {
        val base = getBaseUrl() ?: return null
        return try {
            client.newCall(
                Request.Builder()
                    .url("$base/api/callguard/token")
                    .post("{}".toRequestBody("application/json".toMediaType()))
                    .build(),
            ).execute().use { resp ->
                if (!resp.isSuccessful) null
                else JSONObject(resp.body?.string() ?: return null).optString("token")
            }
        } catch (_: Exception) {
            null
        }
    }

    fun postJson(path: String, jsonBody: String, token: String? = null): Boolean {
        val base = getBaseUrl() ?: return false
        val req = Request.Builder()
            .url("$base$path")
            .post(jsonBody.toRequestBody("application/json".toMediaType()))
            .apply { if (token != null) header("Authorization", "Bearer $token") }
            .build()
        return try {
            client.newCall(req).execute().use { it.isSuccessful }
        } catch (_: Exception) {
            false
        }
    }

    fun ping(): Boolean = connection.probeHealth()

    fun fetchThreatDb(token: String?): String? {
        val base = getBaseUrl() ?: return connection.readCachedThreatDb()
        return try {
            val req = Request.Builder()
                .url("$base/api/callguard/threat-db")
                .get()
                .apply { if (token != null) header("Authorization", "Bearer $token") }
                .build()
            client.newCall(req).execute().use { r ->
                if (r.isSuccessful) {
                    val body = r.body?.string() ?: return connection.readCachedThreatDb()
                    connection.cacheThreatDb(body)
                    body
                } else {
                    connection.readCachedThreatDb()
                }
            }
        } catch (_: Exception) {
            connection.readCachedThreatDb()
        }
    }
}