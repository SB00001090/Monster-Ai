package ai.monster.callguard

import ai.monster.callguard.guardian.GuardianSyncClient
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class GuardianSyncClientTest {

    @Test
    fun bundleTypesIncludeAllGuardianBundles() {
        assertEquals(4, GuardianSyncClient.BUNDLE_TYPES.size)
        assertTrue(GuardianSyncClient.BUNDLE_TYPES.contains("training_vault"))
        assertTrue(GuardianSyncClient.BUNDLE_TYPES.contains("preferences"))
        assertTrue(GuardianSyncClient.BUNDLE_TYPES.contains("oc_cards"))
        assertTrue(GuardianSyncClient.BUNDLE_TYPES.contains("chat_sessions"))
    }
}