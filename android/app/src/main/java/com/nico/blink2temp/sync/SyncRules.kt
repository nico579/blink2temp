package com.nico.blink2temp.sync

/**
 * Règles pures du relevé automatique, testables sans Android.
 */

/**
 * Caméras à relever : la sélection enregistrée, limitée aux caméras encore
 * présentes sur l'écran d'accueil. Sans sélection enregistrée (premier relevé),
 * toutes les caméras découvertes sont retenues.
 */
fun selectedCameraNames(decouvertes: Set<String>, enregistree: Set<String>?): Set<String> =
    enregistree?.intersect(decouvertes) ?: decouvertes

/** Vrai si le dernier relevé est assez récent pour éviter un appel réseau inutile. */
fun isRecentEnough(dernier: Long?, maintenant: Long, intervalMs: Long): Boolean =
    dernier != null && intervalMs > 0 && maintenant - dernier in 0 until intervalMs

/** Délai minimal entre deux réveils automatiques, pour préserver la pile. */
const val WAKE_COOLDOWN_MS = 60 * 60_000L

/**
 * Vrai si un nouveau réveil de caméra est autorisé.
 *
 * Un intervalle nul ou négatif force le réveil (action manuelle explicite).
 */
fun wakeAllowed(dernierReveil: Long?, maintenant: Long, intervalleMs: Long): Boolean =
    intervalleMs <= 0L || dernierReveil == null || maintenant - dernierReveil >= intervalleMs

/**
 * Vrai si la température passive n'a pas évolué depuis la dernière mesure.
 * C'est le seul cas où réveiller la caméra apporte une information nouvelle.
 *
 * Sans mesure précédente, on réveille pour établir une référence. Une caméra
 * sans température n'est jamais réveillée.
 */
fun temperatureUnchanged(
    actuelle: Double?,
    precedente: Double?,
    toleranceC: Double = 0.05,
): Boolean {
    if (actuelle == null) return false
    if (precedente == null) return true
    return kotlin.math.abs(actuelle - precedente) <= toleranceC
}
