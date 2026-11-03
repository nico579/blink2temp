package com.nico.blink2temp

import com.nico.blink2temp.core.CameraCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CameraCatalogTest {
    @Test
    fun nomsDeModeles() {
        assertEquals("Blink Outdoor", CameraCatalog.modelName("catalina"))
        assertEquals("Blink Outdoor Projecteur", CameraCatalog.modelName("catalina_clownfish"))
        assertEquals("Blink Outdoor 4", CameraCatalog.modelName("SEDONA"))
        assertEquals("Blink Mini", CameraCatalog.modelName("owl"))
        assertEquals("Blink Video Doorbell", CameraCatalog.modelName("lotus"))
        assertEquals("Blink Inconnu", CameraCatalog.modelName(null))
        assertEquals("Blink Inconnu", CameraCatalog.modelName("  "))
        assertEquals("Blink (inconnu)", CameraCatalog.modelName("inconnu"))
    }

    @Test
    fun detectionDesCamerasExterieures() {
        assertTrue(CameraCatalog.isOutdoor("catalina", "Jardin"))
        assertTrue(CameraCatalog.isOutdoor("xt2", null))
        assertFalse(CameraCatalog.isOutdoor("owl", "Bureau"))
        assertTrue(CameraCatalog.isOutdoor(null, "Caméra Outdoor"))
        assertTrue(CameraCatalog.isOutdoor("modele_outdoor", null))
        assertFalse(CameraCatalog.isOutdoor(null, null))
    }
}
