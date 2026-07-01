package ai.monster.callguard.network

import okhttp3.Interceptor
import okhttp3.Response
import java.io.IOException

/** Exponential backoff for transient tunnel / QUIC failures. */
class RetryInterceptor(
    private val maxRetries: Int = 3,
    private val baseBackoffMs: Long = 400,
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        var attempt = 0
        var last: IOException? = null
        while (attempt <= maxRetries) {
            try {
                val response = chain.proceed(chain.request())
                if (response.isSuccessful || response.code in 400..499) return response
                response.close()
            } catch (e: IOException) {
                last = e
            }
            attempt++
            if (attempt <= maxRetries) {
                Thread.sleep(baseBackoffMs * attempt)
            }
        }
        throw last ?: IOException("network retry exhausted")
    }
}