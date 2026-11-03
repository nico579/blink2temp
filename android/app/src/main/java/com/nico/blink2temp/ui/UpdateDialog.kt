package com.nico.blink2temp.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.nico.blink2temp.update.UpdatePhase
import com.nico.blink2temp.update.UpdateState
import java.util.Locale

private val UpdateCard = Color(0xFF1E293B)
private val UpdateSky = Color(0xFF38BDF8)

@Composable
internal fun UpdateDialog(
    state: UpdateState,
    onClose: () -> Unit,
    onCheck: () -> Unit,
    onAction: () -> Unit,
) {
    val message = when (state.phase) {
        UpdatePhase.IDLE, UpdatePhase.CHECKING -> "Recherche de mises à jour…"
        UpdatePhase.CURRENT -> "Vous utilisez la dernière version publiée."
        UpdatePhase.AVAILABLE -> "Une nouvelle version est disponible."
        UpdatePhase.DOWNLOADING -> "Téléchargement de la mise à jour…"
        UpdatePhase.VALIDATING -> "Vérification de la mise à jour…"
        UpdatePhase.READY -> "Mise à jour vérifiée. Vous pouvez lancer l'installation."
        UpdatePhase.PERMISSION ->
            "Android demande votre autorisation pour installer une mise à jour depuis Blink2Temp. " +
                "Activez cette autorisation dans les réglages, puis revenez ici."
        UpdatePhase.INSTALLER ->
            "Confirmez l'installation dans la fenêtre Android. Si vous l'avez annulée, vous pouvez réessayer."
        UpdatePhase.ERROR -> state.error ?: "La vérification de la mise à jour a échoué."
    }
    val action = when (state.phase) {
        UpdatePhase.AVAILABLE -> "Télécharger et installer"
        UpdatePhase.PERMISSION -> "Autoriser l'installation"
        UpdatePhase.READY, UpdatePhase.INSTALLER -> "Installer"
        UpdatePhase.ERROR -> "Réessayer"
        else -> "Vérifier à nouveau"
    }

    AlertDialog(
        onDismissRequest = onClose,
        containerColor = UpdateCard,
        title = { Text("Mises à jour") },
        text = {
            Column(
                Modifier.heightIn(max = 300.dp).verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Text("Version installée : ${state.currentVersion}")
                Text(message)
                state.release?.let { release ->
                    val size = String.format(Locale.FRANCE, "%.1f", release.size / 1048576.0)
                    Text("Version ${release.version} disponible · $size Mio")
                    if (release.notes.isNotBlank()) {
                        Text(release.notes, style = MaterialTheme.typography.bodySmall)
                    }
                }
                if (state.busy) {
                    if (state.phase == UpdatePhase.DOWNLOADING && state.total > 0) {
                        LinearProgressIndicator(
                            progress = { (state.completed.toFloat() / state.total).coerceIn(0f, 1f) },
                            modifier = Modifier.fillMaxWidth(),
                            color = UpdateSky,
                        )
                        Text("${(state.completed * 100 / state.total).coerceIn(0, 100)} %")
                    } else {
                        LinearProgressIndicator(Modifier.fillMaxWidth(), color = UpdateSky)
                    }
                }
            }
        },
        confirmButton = {
            if (!state.busy) {
                TextButton(
                    onClick = if (state.phase in setOf(UpdatePhase.IDLE, UpdatePhase.CURRENT)) onCheck else onAction,
                ) {
                    Text(action)
                }
            }
        },
        dismissButton = {
            TextButton(onClick = onClose) { Text(if (state.busy) "Annuler" else "Fermer") }
        },
    )
}
