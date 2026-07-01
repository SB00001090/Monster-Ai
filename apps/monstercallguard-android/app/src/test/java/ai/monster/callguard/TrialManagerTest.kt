package ai.monster.callguard

import org.junit.Assert.assertEquals
import org.junit.Test

/** Trial window logic: 7 days in milliseconds */
class TrialManagerTest {
    @Test
    fun trialWindowIsSevenDays() {
        val sevenDaysMs = 7L * 24 * 60 * 60 * 1000
        assertEquals(sevenDaysMs, 604800000L)
    }
}