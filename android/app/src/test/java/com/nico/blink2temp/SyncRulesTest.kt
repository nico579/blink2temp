package com.nico.blink2temp

import com.nico.blink2temp.sync.isRecentEnough
import com.nico.blink2temp.sync.selectedCameraNames
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SyncRulesTest {
    @Test
    fun premiereSelectionRetientToutesLesCameras() {
        assertEquals(
            setOf("Jardin", "Bureau"),
            selectedCameraNames(setOf("Jardin", "Bureau"), null),
        )
    }

    @Test
    fun selectionEnregistreeLimiteeAuxCamerasPresentes() {
        assertEquals(
            setOf("Jardin"),
            selectedCameraNames(setOf("Jardin", "Bureau"), setOf("Jardin", "Porte")),
        )
        assertEquals(emptySet<String>(), selectedCameraNames(emptySet(), setOf("Jardin")))
    }

    @Test
    fun releveRecentEviteUnAppelReseau() {
        val maintenant = 10_000_000L
        assertTrue(isRecentEnough(maintenant - 60_000L, maintenant, 10 * 60_000L))
        assertFalse(isRecentEnough(maintenant - 11 * 60_000L, maintenant, 10 * 60_000L))
        assertFalse(isRecentEnough(null, maintenant, 10 * 60_000L))
        // Sans intervalle demandé, aucun saut : un relevé manuel reste forcé.
        assertFalse(isRecentEnough(maintenant, maintenant, 0L))
    }
}
