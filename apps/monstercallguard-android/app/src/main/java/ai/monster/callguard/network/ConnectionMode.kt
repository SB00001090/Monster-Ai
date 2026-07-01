package ai.monster.callguard.network

/** USB adb reverse (127.0.0.1) or Cloudflare Tunnel HTTPS. No LAN IP / Tailscale. */
enum class ConnectionMode {
    USB_LOCAL,
    TUNNEL_REMOTE,
    NONE,
}

object UsbBridgeConnection {
    /** PC runs: adb reverse tcp:7860 tcp:7860 — phone uses localhost, no IP input. */
    const val BASE_URL = "http://127.0.0.1:7860"
}