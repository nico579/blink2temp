package com.nico.blink2temp

import com.nico.blink2temp.data.MeasurementStore
import com.nico.blink2temp.data.Reading
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.nio.file.Files
import java.nio.file.Path

class MeasurementStoreTest {
    private lateinit var dossier: Path

    @Before
    fun setUp() {
        dossier = Files.createTempDirectory("blink2temp-test")
    }

    @After
    fun tearDown() {
        dossier.toFile().deleteRecursively()
    }

    private fun lecture(
        timestamp: Long,
        nom: String = "Jardin",
        temperature: Double? = 18.0,
    ) = Reading(
        timestamp = timestamp,
        cameraName = nom,
        cameraId = "1",
        cameraType = "catalina",
        model = "Blink Outdoor",
        outdoor = true,
        tempC = temperature,
        battery = "ok",
        batteryLevel = 3,
        wifi = 4,
        lfr = 1,
        status = "done",
        blinkUpdatedAt = "2026-01-01T10:00:00+00:00",
    )

    @Test
    fun persistanceAllerRetour() {
        val fichier = dossier.resolve("historique.json").toFile()
        val store = MeasurementStore(fichier)
        val maintenant = System.currentTimeMillis()

        store.addAll(
            listOf(
                lecture(maintenant),
                lecture(maintenant + 1_000, "Portail", null),
            ),
        )

        val relu = MeasurementStore(fichier).load()
        assertEquals(2, relu.size)
        assertEquals("Jardin", relu[0].cameraName)
        assertEquals(18.0, relu[0].tempC!!, 0.0001)
        assertEquals(4, relu[0].wifi)
        assertNull(relu[1].tempC)
        assertTrue(fichier.exists())
    }

    @Test
    fun purgeDesMesuresTropAnciennes() {
        val maintenant = 1_700_000_000_000L
        val store = MeasurementStore(dossier.resolve("h.json").toFile(), now = { maintenant })
        val ancienne = maintenant - 40L * 86_400_000L
        val recente = maintenant - 2L * 86_400_000L

        val historique = store.addAll(listOf(lecture(ancienne), lecture(recente)))

        assertEquals(1, historique.size)
        assertEquals(recente, historique[0].timestamp)
    }

    @Test
    fun plafondDuNombreDEntrees() {
        val maintenant = 1_700_000_000_000L
        val store = MeasurementStore(
            dossier.resolve("plafond.json").toFile(),
            now = { maintenant },
            maxEntries = 10,
        )
        val mesures = (1..15).map { index ->
            lecture(maintenant - (15 - index) * 1_000L)
        }

        val historique = store.addAll(mesures)

        assertEquals(10, historique.size)
        // Les 5 mesures les plus anciennes sont écartées.
        assertEquals(maintenant - 9_000L, historique.first().timestamp)
        assertEquals(maintenant, historique.last().timestamp)
    }

    @Test
    fun statistiquesParCamera() {
        val maintenant = 1_700_000_000_000L
        val store = MeasurementStore(dossier.resolve("stats.json").toFile(), now = { maintenant })
        store.addAll(
            listOf(
                lecture(maintenant - 3_000, "Jardin", 10.0),
                lecture(maintenant - 2_000, "Jardin", 20.0),
                lecture(maintenant - 1_000, "Jardin", 30.0),
                lecture(maintenant, "Portail", 5.0),
                lecture(maintenant, "Jardin", null),
                lecture(maintenant - 10L * 86_400_000L, "Jardin", 99.0),
            ),
        )

        val stats = store.stats(maintenant - 3_600_000L)

        assertEquals(2, stats.size)
        val jardin = stats.getValue("Jardin")
        assertEquals(3, jardin.count)
        assertEquals(10.0, jardin.minC, 0.0001)
        assertEquals(20.0, jardin.avgC, 0.0001)
        assertEquals(30.0, jardin.maxC, 0.0001)
        assertEquals(1, stats.getValue("Portail").count)
    }

    @Test
    fun effacement() {
        val fichier = dossier.resolve("clear.json").toFile()
        val store = MeasurementStore(fichier)
        store.addAll(listOf(lecture(System.currentTimeMillis())))

        store.clear()

        assertEquals(0, store.load().size)
        assertFalse(fichier.exists())
    }
}
