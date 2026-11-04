package com.nico.blink2temp.sync

import android.content.Context
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

/**
 * Planification du relevé automatique.
 *
 * WorkManager est la méthode recommandée par Android : la tâche survit à la
 * fermeture de l'application et au redémarrage du téléphone. La première
 * exécution est différée d'un intervalle, car l'ouverture de l'application
 * effectue déjà un relevé.
 */
object ReadingScheduler {
    private const val WORK_NAME = "blink2temp-releve-automatique"
    const val INTERVAL_MINUTES = 15L

    fun schedule(context: Context) {
        val demande = PeriodicWorkRequestBuilder<ReadingWorker>(
            INTERVAL_MINUTES,
            TimeUnit.MINUTES,
        )
            .setConstraints(
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .build(),
            )
            .setInitialDelay(INTERVAL_MINUTES, TimeUnit.MINUTES)
            .build()

        // KEEP : ouvrir l'application ne remet pas le compteur à zéro.
        WorkManager.getInstance(context)
            .enqueueUniquePeriodicWork(WORK_NAME, ExistingPeriodicWorkPolicy.KEEP, demande)
    }

    fun cancel(context: Context) {
        WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
    }
}
