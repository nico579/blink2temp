package com.nico.blink2temp.core

import java.util.Locale

/** Catalogue des modèles Blink et détection des caméras extérieures. */
object CameraCatalog {
    private val MODELS: Map<String, String> = mapOf(
        "catalina" to "Blink Outdoor",
        "catalina_clownfish" to "Blink Outdoor Projecteur",
        "sedona" to "Blink Outdoor 4",
        "canary" to "Blink XT",
        "xt" to "Blink XT",
        "xt2" to "Blink XT2",
        "owl" to "Blink Mini",
        "lotus" to "Blink Video Doorbell",
        "sm" to "Sync Module",
        "sm2" to "Sync Module 2",
    )

    val OUTDOOR_TYPES: Set<String> = setOf(
        "catalina",
        "catalina_clownfish",
        "sedona",
        "canary",
        "xt",
        "xt2",
    )

    /** Traduit le nom de code interne Amazon (ex : « catalina ») en nom commercial. */
    fun modelName(type: String?): String {
        val code = type?.trim()?.lowercase(Locale.ROOT).orEmpty()
        if (code.isEmpty()) return "Blink Inconnu"
        return MODELS[code] ?: "Blink ($code)"
    }

    /** Reproduit la détection du collecteur Python (type matériel ou nom « outdoor »). */
    fun isOutdoor(type: String?, name: String?): Boolean {
        val code = type?.trim()?.lowercase(Locale.ROOT).orEmpty()
        val nom = name?.trim()?.lowercase(Locale.ROOT).orEmpty()
        if (code in OUTDOOR_TYPES) return true
        return "outdoor" in code || "outdoor" in nom
    }
}
