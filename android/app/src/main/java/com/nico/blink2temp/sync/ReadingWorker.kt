package com.nico.blink2temp.sync

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.nico.blink2temp.blink.BlinkAuthException
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Relevé périodique exécuté par WorkManager, même application fermée.
 *
 * La session et la sélection de caméras sont lues depuis le stockage local :
 * aucun mot de passe n'est nécessaire en arrière-plan.
 */
class ReadingWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        try {
            ReadingSync.run(
                context = applicationContext,
                skipIfFreshMs = 10 * 60_000L,
            )
            Result.success()
        } catch (annulation: CancellationException) {
            throw annulation
        } catch (_: BlinkAuthException) {
            // Jeton refusé : l'utilisateur devra se reconnecter dans l'interface.
            Result.failure()
        } catch (_: Exception) {
            // Réseau indisponible ou Blink momentanément injoignable.
            Result.retry()
        }
    }
}
