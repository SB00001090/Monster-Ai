package ai.monster.callguard.network

import android.content.Context

/** Cloudflare Tunnel URL validation — no IP / Tailscale / LAN discovery. */
object TunnelConnection {
    private val URL_PATTERN = Regex(
        "^https://[a-z0-9][a-z0-9-]*\\.trycloudflare\\.com/?$",
        RegexOption.IGNORE_CASE,
    )
    private val NAMED_TUNNEL_PATTERN = Regex(
        "^https://[a-z0-9][a-z0-9.-]*\\.(pages\\.dev|monster-ai\\.com)/?$",
        RegexOption.IGNORE_CASE,
    )

    fun normalizeUrl(raw: String?): String? {
        if (raw.isNullOrBlank()) return null
        var u = raw.trim().trimEnd('/')
        if (!u.startsWith("http://") && !u.startsWith("https://")) {
            u = "https://$u"
        }
        if (u.contains(":7860")) return null
        if (URL_PATTERN.matches(u) || NAMED_TUNNEL_PATTERN.matches(u)) return u
        if (u.contains("trycloudflare.com") && u.startsWith("https://")) return u
        return null
    }

    fun validateOrError(raw: String): String? {
        val n = normalizeUrl(raw)
        if (n != null) return null
        return when {
            raw.contains("100.") || raw.contains("ts.net") || raw.contains("tailscale", true) ->
                "已移除 Tailscale — 請使用 Cloudflare Tunnel HTTPS URL"
            raw.matches(Regex(".*\\d{1,3}(\\.\\d{1,3}){3}.*")) ->
                "唔使輸入 IP — 請貼上 https://xxx.trycloudflare.com"
            raw.contains(":7860") ->
                "請勿加 :7860 — 只貼 Tunnel 公開 HTTPS 網址"
            else -> "無效 URL — 例：https://your-name.trycloudflare.com"
        }
    }

    fun loadSaved(context: Context): String? {
        val prefs = context.getSharedPreferences("callguard", Context.MODE_PRIVATE)
        return normalizeUrl(prefs.getString("tunnel_url", null))
    }

    fun setupHint(): String = buildString {
        append("連線方式（二選一）：\n\n")
        append("【USB 本機】電腦執行 install-apk-adb.bat\n")
        append("  手機 USB 偵錯 + adb reverse，唔使輸入 IP\n\n")
        append("【Tunnel 遠端】\n")
        append("  1) python main.py  2) run-tunnel.bat\n")
        append("  3) 貼 https://*.trycloudflare.com\n")
        append("\nDeveloped by Suckbob | Monster AI Call Guard")
    }

    fun failureHint(): String = buildString {
        append("連線失敗\n")
        append("• USB：install-apk-adb.bat（需開啟 USB 偵錯）\n")
        append("• 遠端：run-tunnel.bat 後更新 Tunnel URL\n")
        append("• 離線仍可用本機威脅資料庫快取")
    }
}