package ai.monster.callguard

import ai.monster.callguard.network.TunnelConnection
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class TunnelConnectionTest {
    @Test
    fun acceptsTryCloudflareUrl() {
        val url = "https://requirements-controversy-length-pam.trycloudflare.com"
        assertEquals(url, TunnelConnection.normalizeUrl(url))
    }

    @Test
    fun rejectsIpAddress() {
        assertNull(TunnelConnection.normalizeUrl("http://192.168.0.4:7860"))
        assertNotNull(TunnelConnection.validateOrError("192.168.0.4"))
    }

    @Test
    fun rejectsTailscale() {
        assertNull(TunnelConnection.normalizeUrl("100.89.138.96"))
        assertNotNull(TunnelConnection.validateOrError("tm0721.taile4ca68.ts.net"))
    }

    @Test
    fun rejectsPort7860() {
        assertNull(
            TunnelConnection.normalizeUrl(
                "https://foo.trycloudflare.com:7860",
            ),
        )
    }
}