package com.nico.blink2temp

import com.nico.blink2temp.sync.isRecentEnough
import com.nico.blink2temp.sync.selectedCameraNames
import com.nico.blink2temp.sync.temperatureUnchanged
import com.nico.blink2temp.sync.wakeAllowed
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

    @Test
    fun reveilSeulementSiLaTemperatureNaPasEvolue() {
        // Température identique (aux arrondis près) : on réveille.
        assertTrue(temperatureUnchanged(12.3, 12.3))
        assertTrue(temperatureUnchanged(12.3, 12.32))
        // La température a bougé : le relevé passif suffit, on économise la pile.
        assertFalse(temperatureUnchanged(12.3, 12.9))
        // Première mesure : on établit une référence.
        assertTrue(temperatureUnchanged(12.3, null))
        // Une caméra sans température n'est jamais réveillée.
        assertFalse(temperatureUnchanged(null, 12.3))
        assertFalse(temperatureUnchanged(null, null))
    }

    @Test
    fun cooldownDeReveilRespecte() {
        val maintenant = 10_000_000L
        val heure = 60 * 60_000L
        assertTrue(wakeAllowed(null, maintenant, heure))
        assertFalse(wakeAllowed(maintenant - 30 * 60_000L, maintenant, heure))
        assertTrue(wakeAllowed(maintenant - heure, maintenant, heure))
        // Un relevé manuel force le réveil, sans attendre le cooldown.
        assertTrue(wakeAllowed(maintenant - 60_000L, maintenant, 0L))
    }
}
