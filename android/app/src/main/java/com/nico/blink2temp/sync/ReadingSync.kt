package com.nico.blink2temp.sync

import android.content.Context
import com.nico.blink2temp.blink.BlinkClient
import com.nico.blink2temp.blink.BlinkSession
import com.nico.blink2temp.blink.CameraInfo
import com.nico.blink2temp.data.MeasurementStore
import com.nico.blink2temp.data.Reading
import com.nico.blink2temp.data.SessionStore
import com.nico.blink2temp.data.toReading
import java.io.File

/** Résultat d'un relevé, utilisé par l'interface pour rafraîchir son état. */
data class SyncResult(
    val session: BlinkSession,
    val cameras: List<CameraInfo>,
    val selection: Set<String>,
    val readings: List<Reading>,
    val timestamp: Long,
)

/**
 * Relevé partagé entre l'interface et le worker d'arrière-plan.
 *
 * Le verrou couvre le rafraîchissement du jeton, la lecture de l'écran
 * d'accueil et l'écriture de l'historique : deux relevés simultanés ne peuvent
 * ni perdre de mesures, ni réutiliser deux fois le même refresh token.
 */
object ReadingSync {
    private val verrou = Any()

    fun run(
        context: Context,
        client: BlinkClient = BlinkClient(),
        skipIfFreshMs: Long = 0L,
        now: () -> Long = { System.currentTimeMillis() },
    ): SyncResult? = synchronized(verrou) {
        val sessions = SessionStore(context)
        var session = sessions.loadSession() ?: return null
        val store = MeasurementStore(File(context.filesDir, "historique.json"))
        val maintenant = now()

        // Un relevé manuel vient peut-être d'avoir lieu : inutile de réveiller
        // le réseau pour un worker planifié juste après.
        if (isRecentEnough(store.load().maxOfOrNull { it.timestamp }, maintenant, skipIfFreshMs)) {
            return null
        }

        if (session.expiresAt - 120_000L <= maintenant) {
            session = client.refreshSession(session)
            sessions.saveSession(session)
        }

        val cameras = client.fetchCameras(session)
        val noms = cameras.map { it.name }.toSet()
        val enregistree = sessions.loadSelection()
        val selection = selectedCameraNames(noms, enregistree)
        val nouvelles = cameras
            .filter { it.name in selection }
            .map { it.toReading(maintenant) }
        val historique = store.addAll(nouvelles)
        if (enregistree != selection) sessions.saveSelection(selection)

        SyncResult(
            session = session,
            cameras = cameras,
            selection = selection,
            readings = historique,
            timestamp = maintenant,
        )
    }
}
