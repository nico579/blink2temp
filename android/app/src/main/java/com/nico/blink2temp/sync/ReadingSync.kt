package com.nico.blink2temp.sync

import android.content.Context
import com.nico.blink2temp.blink.BlinkAuthException
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
    /** Caméras dont le réveil a échoué (la lecture reste valable mais ancienne). */
    val wakeFailures: List<String> = emptyList(),
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
        wake: Boolean = false,
        respectWakeCooldown: Boolean = true,
        now: () -> Long = { System.currentTimeMillis() },
    ): SyncResult? = synchronized(verrou) {
        val sessions = SessionStore(context)
        var session = sessions.loadSession() ?: return null
        val store = MeasurementStore(File(context.filesDir, "historique.json"))
        val maintenant = now()
        val historiqueActuel = store.load()

        // Un relevé manuel vient peut-être d'avoir lieu : inutile de réveiller
        // le réseau pour un worker planifié juste après.
        if (isRecentEnough(historiqueActuel.maxOfOrNull { it.timestamp }, maintenant, skipIfFreshMs)) {
            return null
        }

        // Dernière température connue par caméra, pour ne réveiller que celles
        // dont la lecture passive n'a pas bougé.
        val dernieresTemperatures = historiqueActuel
            .groupBy { it.cameraName }
            .mapValues { (_, mesures) -> mesures.maxByOrNull { it.timestamp }?.tempC }

        if (session.expiresAt - 120_000L <= maintenant) {
            session = client.refreshSession(session)
            sessions.saveSession(session)
        }

        var cameras = client.fetchCameras(session)
        var noms = cameras.map { it.name }.toSet()
        val enregistree = sessions.loadSelection()
        var selection = selectedCameraNames(noms, enregistree)

        val echecs = mutableListOf<String>()
        if (wake) {
            val dernierReveil = sessions.loadLastWake()
            val autorise = !respectWakeCooldown ||
                wakeAllowed(dernierReveil, maintenant, WAKE_COOLDOWN_MS)
            if (autorise) {
                var reveillee = false
                // Une seule caméra à la fois : le module de synchronisation
                // relaie les commandes en série.
                for (camera in cameras.filter { it.name in selection }) {
                    // Température déjà à jour : inutile de consommer la pile.
                    if (!temperatureUnchanged(camera.tempC, dernieresTemperatures[camera.name])) {
                        continue
                    }
                    try {
                        if (client.wakeCamera(session, camera)) {
                            reveillee = true
                        } else {
                            echecs += camera.name
                        }
                    } catch (auth: BlinkAuthException) {
                        throw auth
                    } catch (_: Exception) {
                        echecs += camera.name
                    }
                }
                if (reveillee) {
                    sessions.saveLastWake(now())
                    // Blink publie la température rapportée par la caméra qui
                    // vient de se réveiller dans l'écran d'accueil.
                    cameras = client.fetchCameras(session)
                    noms = cameras.map { it.name }.toSet()
                    selection = selectedCameraNames(noms, enregistree)
                }
            }
        }

        val horodatage = now()
        val nouvelles = cameras
            .filter { it.name in selection }
            .map { it.toReading(horodatage) }
        val historique = store.addAll(nouvelles)
        if (enregistree != selection) sessions.saveSelection(selection)

        SyncResult(
            session = session,
            cameras = cameras,
            selection = selection,
            readings = historique,
            timestamp = horodatage,
            wakeFailures = echecs,
        )
    }
}
