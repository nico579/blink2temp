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
