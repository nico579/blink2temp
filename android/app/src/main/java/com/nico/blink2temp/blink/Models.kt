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

/**
 * Hôte de l'API Blink à partir du tier renvoyé par `tier_info`.
 *
 * Blink renvoie par exemple `prod`, alors que l'API est servie par
 * `rest-prod.immedia-semi.com` : sans le préfixe `rest-`, la résolution DNS
 * échoue et l'application affiche à tort « Pas de connexion Internet ».
 */
fun blinkApiHost(tier: String): String {
    val valeur = tier.trim().trimEnd('.')
    if (valeur.isEmpty()) return ""
    if (valeur.endsWith(".immedia-semi.com")) return normalizeBlinkHost(valeur)
    val sousDomaine = if (valeur.startsWith("rest-")) valeur else "rest-$valeur"
    return "$sousDomaine.immedia-semi.com"
}

/** Corrige un hôte enregistré par une version antérieure (0.1.0 / 0.1.1). */
fun normalizeBlinkHost(host: String): String {
    val valeur = host.trim().trimEnd('.')
    if (valeur.isEmpty()) return ""
    return if (valeur.startsWith("rest-")) valeur else "rest-$valeur"
}
