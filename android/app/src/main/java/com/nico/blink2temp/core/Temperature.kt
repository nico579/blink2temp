package com.nico.blink2temp.core

import java.util.Locale
import kotlin.math.round

/** Unité de température affichée dans toute l'application. */
enum class TemperatureUnit(val symbol: String) {
    CELSIUS("°C"),
    FAHRENHEIT("°F");

    /** Convertit une valeur stockée en °C vers l'unité affichée (null conservé). */
    fun fromCelsius(celsius: Double?): Double? = when {
        celsius == null -> null
        this == CELSIUS -> celsius
        else -> celsius * 9.0 / 5.0 + 32.0
    }

    /** Formate une valeur en °C dans l'unité choisie, avec une décimale. */
    fun format(celsius: Double?): String {
        val valeur = fromCelsius(celsius) ?: return "--"
        return Temperature.formatValue(valeur) + symbol
    }
}

object Temperature {
    /** Territoires qui utilisent le Fahrenheit (même liste que la page web). */
    val FAHRENHEIT_REGIONS: Set<String> = setOf(
        "AS", "BQ", "BS", "FM", "GU", "IO", "JM", "KY", "LR", "MH", "MM",
        "MP", "PW", "PR", "PS", "SX", "TC", "TL", "UM", "US", "VG", "VI",
    )

    /** Convertit des °F Blink en °C arrondis à 0,1 °C. */
    fun fahrenheitToCelsius(fahrenheit: Double?): Double? {
        if (fahrenheit == null || !fahrenheit.isFinite()) return null
        return round1((fahrenheit - 32.0) * 5.0 / 9.0)
    }

    fun round1(valeur: Double): Double {
        if (!valeur.isFinite()) return valeur
        return round(valeur * 10.0) / 10.0
    }

    /** Format à une décimale avec point décimal, comme la page web. */
    fun formatValue(valeur: Double): String = String.format(Locale.US, "%.1f", valeur)

    /** Choisit l'unité d'après le territoire de la locale (US et assimilés → °F). */
    fun unitForRegion(region: String?): TemperatureUnit {
        val code = region?.trim()?.uppercase(Locale.ROOT).orEmpty()
        return if (code in FAHRENHEIT_REGIONS) TemperatureUnit.FAHRENHEIT else TemperatureUnit.CELSIUS
    }

    fun unitFor(locale: Locale): TemperatureUnit = unitForRegion(locale.country)
}
