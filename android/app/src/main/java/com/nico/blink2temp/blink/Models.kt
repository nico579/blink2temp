package com.nico.blink2temp.blink

import com.nico.blink2temp.core.CameraCatalog
import com.nico.blink2temp.core.Temperature
import org.json.JSONObject

/** Session OAuth v2 persistée entre deux lancements. */
data class BlinkSession(
    val username: String,
    val hardwareId: String,
    val accessToken: String,
    val refreshToken: String,
    val expiresAt: Long,
    val host: String,
    val accountId: String,
)

/** Caméra telle que renvoyée par l'écran d'accueil Blink. */
data class CameraInfo(
    val id: String,
    val name: String,
    val type: String,
    val model: String,
    val outdoor: Boolean,
    val tempC: Double?,
    val tempF: Double?,
    val battery: String,
    val batteryLevel: Int?,
    val wifi: Int?,
    val lfr: Int?,
    val status: String,
    val updatedAt: String?,
)

/**
 * Extrait toutes les caméras de la réponse `/homescreen` (caméras, Minis et
 * sonnettes). Les doublons de nom sont ignorés.
 */
fun parseHomescreen(body: String): List<CameraInfo> {
    val racine = JSONObject(body)
    val resultat = LinkedHashMap<String, CameraInfo>()
    for (groupe in listOf("cameras", "owls", "doorbells")) {
        val appareils = racine.optJSONArray(groupe) ?: continue
        for (index in 0 until appareils.length()) {
            val objet = appareils.optJSONObject(index) ?: continue
            val camera = parseCamera(objet, groupe)
            if (camera.name.isNotBlank() && !resultat.containsKey(camera.name)) {
                resultat[camera.name] = camera
            }
        }
    }
    return resultat.values.sortedBy { it.name.lowercase() }
}

fun parseCamera(objet: JSONObject, groupe: String = "cameras"): CameraInfo {
    val type = objet.optString("type").trim().ifBlank {
        when (groupe) {
            "owls" -> "owl"
            "doorbells" -> "lotus"
            else -> ""
        }
    }
    val nom = objet.optString("name").trim().ifBlank { "Caméra" }
    val identifiant = listOf("id", "device_id", "camera_id")
        .mapNotNull { cle ->
            objet.opt(cle)?.toString()?.takeIf { it.isNotBlank() && it != "null" }
        }
        .firstOrNull()
        .orEmpty()

    val signaux = objet.optJSONObject("signals")
    val tempF = (signaux?.opt("temp") as? Number)?.toDouble()
    val modele = CameraCatalog.modelName(type)

    return CameraInfo(
        id = identifiant,
        name = nom,
        type = type,
        model = modele,
        outdoor = CameraCatalog.isOutdoor(type, nom),
        tempC = Temperature.fahrenheitToCelsius(tempF),
        tempF = tempF,
        battery = objet.optString("battery").trim(),
        batteryLevel = signaux?.optIntOrNull("battery"),
        wifi = signaux?.optIntOrNull("wifi"),
        lfr = signaux?.optIntOrNull("lfr"),
        status = objet.optString("status").trim(),
        updatedAt = objet.optString("updated_at").trim().takeIf { it.isNotBlank() },
    )
}

private fun JSONObject.optIntOrNull(cle: String): Int? = when (val valeur = opt(cle)) {
    null, JSONObject.NULL -> null
    is Number -> valeur.toInt()
    is String -> valeur.toIntOrNull()
    else -> null
}
