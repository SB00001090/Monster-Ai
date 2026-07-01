package ai.monster.callguard.engine

import ai.monster.callguard.network.HomeMonsterClient
import ai.monster.callguard.security.CredentialBridge
import android.content.Context

class RemoteAnalyzer(
    private val context: Context,
    private val client: HomeMonsterClient,
    private val local: LocalThreatEngine,
) {
    fun analyze(number: String, displayName: String): CallScore {
        val localScore = local.score(number, displayName)
        if (localScore.reject) return localScore
        if (localScore.score < 60) return localScore

        val token = CredentialBridge.getToken(context)
        val remote = client.analyzeRemote(number, displayName, token) ?: return localScore
        val score = remote.optInt("score", localScore.score)
        val trust = remote.optInt("trust_score", maxOf(0, 100 - score))
        val reject = remote.optBoolean("reject", score >= 85)
        val category = remote.optString("category", localScore.category)
        val signals = localScore.signals.toMutableList()
        signals.add("remote:monster_ai")
        if (trust < 30) signals.add("trust:low")
        return CallScore(
            score = score,
            reject = reject,
            category = category,
            signals = signals,
        )
    }
}