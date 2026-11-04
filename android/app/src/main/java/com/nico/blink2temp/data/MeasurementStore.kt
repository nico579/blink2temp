package com.nico.blink2temp.data

import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * Historique local des mesures, persisté dans un fichier JSON.
 *
 * Le fichier est purgé à chaque écriture : mesures de plus de 30 jours
 * supprimées puis plafond de 5000 entrées (les plus récentes conservées).
 */
class MeasurementStore(
    private val file: File,
    private val now: () -> Long = { System.currentTimeMillis() },
    private val retentionDays: Int = 30,
    private val maxEntries: Int = 5000,
) {
    private companion object {
        /**
         * Verrou commun à toutes les instances : l'interface et le worker
         * d'arrière-plan écrivent le même fichier d'historique.
         */
        val FICHIER_VERROU = Any()
    }

    private val lock = FICHIER_VERROU

    fun load(): List<Reading> = synchronized(lock) { readFile() }

    /** Ajoute des mesures, purge l'historique et renvoie l'historique à jour. */
    fun addAll(readings: List<Reading>): List<Reading> = synchronized(lock) {
        val historique = prune(readFile() + readings)
        writeFile(historique)
        historique
    }

    fun clear() = synchronized(lock) {
        file.delete()
        File(file.parentFile, file.name + ".tmp").delete()
    }

    /** Min / moyenne / max par caméra pour les mesures postérieures à [since]. */
    fun stats(since: Long): Map<String, CameraStats> = synchronized(lock) {
        readFile()
            .asSequence()
            .filter { it.timestamp >= since && it.tempC != null }
            .groupBy { it.cameraName }
            .mapNotNull { (nom, mesures) ->
                val temperatures = mesures.mapNotNull { it.tempC }
                if (temperatures.isEmpty()) null
                else nom to CameraStats(
                    count = temperatures.size,
                    minC = temperatures.min(),
                    avgC = temperatures.average(),
                    maxC = temperatures.max(),
                )
            }
            .toMap()
    }

    private fun prune(readings: List<Reading>): List<Reading> {
        val cutoff = now() - retentionDays * 86_400_000L
        val recentes = readings.filter { it.timestamp >= cutoff }.sortedBy { it.timestamp }
        return if (recentes.size > maxEntries) recentes.takeLast(maxEntries) else recentes
    }

    private fun readFile(): List<Reading> {
        if (!file.exists()) return emptyList()
        return try {
            val tableau = JSONArray(file.readText(Charsets.UTF_8))
            (0 until tableau.length()).mapNotNull { index ->
                tableau.optJSONObject(index)?.let(::decode)
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun writeFile(readings: List<Reading>) {
        try {
            file.parentFile?.mkdirs()
            val tableau = JSONArray()
            readings.forEach { tableau.put(encode(it)) }
            val contenu = tableau.toString()
            val temporaire = File(file.parentFile, file.name + ".tmp")
            temporaire.writeText(contenu, Charsets.UTF_8)
            if (file.exists() && !file.delete()) {
                file.writeText(contenu, Charsets.UTF_8)
                temporaire.delete()
                return
            }
            if (!temporaire.renameTo(file)) {
                file.writeText(contenu, Charsets.UTF_8)
                temporaire.delete()
            }
        } catch (_: Exception) {
            // Stockage indisponible : l'historique en mémoire reste utilisable.
        }
    }

    internal fun encode(reading: Reading): JSONObject = JSONObject().apply {
        put("t", reading.timestamp)
        put("camera", reading.cameraName)
        put("id", reading.cameraId)
        put("type", reading.cameraType)
        put("model", reading.model)
        put("outdoor", reading.outdoor)
        put("temp_c", reading.tempC ?: JSONObject.NULL)
        put("battery", reading.battery)
        put("battery_level", reading.batteryLevel ?: JSONObject.NULL)
        put("wifi", reading.wifi ?: JSONObject.NULL)
        put("lfr", reading.lfr ?: JSONObject.NULL)
        put("status", reading.status)
        put("blink_updated_at", reading.blinkUpdatedAt ?: JSONObject.NULL)
    }

    internal fun decode(objet: JSONObject): Reading? {
        val nom = objet.optString("camera").trim()
        if (nom.isEmpty()) return null
        return Reading(
            timestamp = objet.optLong("t"),
            cameraName = nom,
            cameraId = objet.optString("id"),
            cameraType = objet.optString("type"),
            model = objet.optString("model"),
            outdoor = objet.optBoolean("outdoor", false),
            tempC = (objet.opt("temp_c") as? Number)?.toDouble(),
            battery = objet.optString("battery"),
            batteryLevel = (objet.opt("battery_level") as? Number)?.toInt(),
            wifi = (objet.opt("wifi") as? Number)?.toInt(),
            lfr = (objet.opt("lfr") as? Number)?.toInt(),
            status = objet.optString("status"),
            blinkUpdatedAt = objet.optString("blink_updated_at").takeIf { it.isNotBlank() },
        )
    }
}
