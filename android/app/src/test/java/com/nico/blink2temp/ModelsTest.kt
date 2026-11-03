package com.nico.blink2temp

import com.nico.blink2temp.blink.parseCamera
import com.nico.blink2temp.blink.parseHomescreen
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ModelsTest {
    private val homescreen = """
        {
          "cameras": [
            {"id": 101, "name": "Jardin", "type": "catalina", "battery": "ok", "status": "done",
             "updated_at": "2026-11-03T10:00:00+00:00",
             "signals": {"temp": 50, "battery": 3, "wifi": 4, "lfr": 1}},
            {"id": 102, "name": "Bureau", "type": "owl", "battery": "low", "status": "offline",
             "signals": {"wifi": 2}}
          ],
          "owls": [
            {"id": 201, "name": "Mini", "type": "owl", "signals": {"temp": 68}}
          ],
          "doorbells": [
            {"id": 301, "name": "Porte", "type": "lotus", "battery": "ok", "signals": {"temp": 59}}
          ]
        }
    """.trimIndent()

    @Test
    fun analyseDeLEcranDAccueil() {
        val cameras = parseHomescreen(homescreen)

        assertEquals(4, cameras.size)
        assertEquals(listOf("Bureau", "Jardin", "Mini", "Porte"), cameras.map { it.name })

        val jardin = cameras.first { it.name == "Jardin" }
        assertEquals("Blink Outdoor", jardin.model)
        assertTrue(jardin.outdoor)
        assertEquals(10.0, jardin.tempC!!, 0.0001)
        assertEquals(50.0, jardin.tempF!!, 0.0001)
        assertEquals(3, jardin.batteryLevel)
        assertEquals(4, jardin.wifi)
        assertEquals("done", jardin.status)
        assertEquals("2026-11-03T10:00:00+00:00", jardin.updatedAt)

        val bureau = cameras.first { it.name == "Bureau" }
        assertFalse(bureau.outdoor)
        assertNull(bureau.tempC)
        assertEquals("Blink Mini", bureau.model)

        val porte = cameras.first { it.name == "Porte" }
        assertEquals("Blink Video Doorbell", porte.model)
        assertEquals(15.0, porte.tempC!!, 0.0001)
    }

    @Test
    fun typeDeduitDuGroupe() {
        val mini = parseCamera(JSONObject("""{"id":1,"name":"Mini","signals":{"temp":70}}"""), "owls")
        assertEquals("owl", mini.type)
        assertEquals("Blink Mini", mini.model)
        assertEquals(21.1, mini.tempC!!, 0.0001)

        val sonnette = parseCamera(JSONObject("""{"id":2,"name":"Porte"}"""), "doorbells")
        assertEquals("lotus", sonnette.type)
        assertEquals("Blink Video Doorbell", sonnette.model)
    }

    @Test
    fun doublonsDeNomIgnores() {
        val json = """
            {"cameras":[{"id":1,"name":"Jardin","type":"catalina"}],
             "owls":[{"id":2,"name":"Jardin","type":"owl"}]}
        """.trimIndent()
        val cameras = parseHomescreen(json)
        assertEquals(1, cameras.size)
        assertEquals("catalina", cameras.first().type)
    }
}
