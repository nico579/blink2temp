package com.nico.blink2temp.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Email
import androidx.compose.material.icons.rounded.Lock
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.nico.blink2temp.UiState
import com.nico.blink2temp.blink.CameraInfo
import com.nico.blink2temp.core.Temperature
import com.nico.blink2temp.core.TemperatureUnit
import com.nico.blink2temp.data.CameraStats
import com.nico.blink2temp.data.Reading
import com.nico.blink2temp.update.UpdateState
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.log10
import kotlin.math.pow

private val Background = Color(0xFF0B1120)
private val CardColor = Color(0xFF1E293B)
private val CardSoft = Color(0xFF16213A)
private val Sky = Color(0xFF38BDF8)
private val TextMain = Color(0xFFE2E8F0)
private val Muted = Color(0xFF94A3B8)
private val Border = Color(0xFF334155)
private val Green = Color(0xFF34D399)
private val Orange = Color(0xFFFB923C)
private val Red = Color(0xFFF87171)
private val DarkOnSky = Color(0xFF06121E)

private val CameraPalette = listOf(
    Sky,
    Orange,
    Green,
    Color(0xFFA78BFA),
    Color(0xFFF472B6),
    Color(0xFFFACC15),
    Color(0xFF22D3EE),
    Color(0xFF818CF8),
)

private val DarkScheme = darkColorScheme(
    primary = Sky,
    onPrimary = DarkOnSky,
    background = Background,
    onBackground = TextMain,
    surface = CardColor,
    onSurface = TextMain,
    surfaceVariant = Color(0xFF172033),
    onSurfaceVariant = Muted,
    outline = Border,
    secondary = Green,
    error = Red,
)

@Composable
fun BlinkScreen(
    state: UiState,
    onConnect: (String, String, Boolean) -> Unit,
    onTwoFactor: (String) -> Unit,
    onCancelTwoFactor: () -> Unit,
    onRefresh: () -> Unit,
    onToggleCamera: (String) -> Unit,
    onSelectAll: () -> Unit,
    onSelectNone: () -> Unit,
    onToggleWakeCameras: () -> Unit,
    onWindowChange: (Int) -> Unit,
    onLogout: () -> Unit,
    onClearHistory: () -> Unit,
    onDismissMessage: () -> Unit,
    updateState: UpdateState = UpdateState(),
    onUpdates: () -> Unit = {},
    onUpdateClose: () -> Unit = {},
    onUpdateCheck: () -> Unit = {},
    onUpdateAction: () -> Unit = {},
) {
    MaterialTheme(colorScheme = DarkScheme) {
        Scaffold(containerColor = Background) { padding ->
            Box(Modifier.fillMaxSize().padding(padding)) {
                Column(Modifier.fillMaxSize().padding(horizontal = 16.dp)) {
                    AppHeader(state, onLogout, onUpdates)
                    state.error?.let { MessageBanner(it, true, onDismissMessage) }
                    state.notice?.let { MessageBanner(it, false, onDismissMessage) }

                    if (state.session == null) {
                        LoginPanel(state, onConnect, onUpdates)
                    } else {
                        Dashboard(
                            state = state,
                            onRefresh = onRefresh,
                            onToggleCamera = onToggleCamera,
                            onSelectAll = onSelectAll,
                            onSelectNone = onSelectNone,
                            onToggleWakeCameras = onToggleWakeCameras,
                            onWindowChange = onWindowChange,
                            onClearHistory = onClearHistory,
                            onUpdates = onUpdates,
                        )
                    }
                }
                if (state.busy) BusyOverlay(state.busyLabel)
            }
        }

        if (state.awaitingTwoFactor) {
            TwoFactorDialog(state, onTwoFactor, onCancelTwoFactor)
        }

        if (updateState.open) {
            UpdateDialog(updateState, onUpdateClose, onUpdateCheck, onUpdateAction)
        }
    }
}

@Composable
private fun AppHeader(state: UiState, onLogout: () -> Unit, onUpdates: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().padding(top = 14.dp, bottom = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("🌡️", fontSize = 26.sp)
        Spacer(Modifier.width(10.dp))
        Column(Modifier.weight(1f)) {
            Text("Blink2Temp", fontSize = 20.sp, fontWeight = FontWeight.Bold)
            Text(
                if (state.session == null) "Relevé de température Blink"
                else state.session.username.ifBlank { "Compte Blink" },
                fontSize = 12.sp,
                color = Muted,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        Box(
            Modifier.background(Sky.copy(alpha = 0.15f), RoundedCornerShape(50))
                .padding(horizontal = 10.dp, vertical = 4.dp),
        ) {
            Text(state.unit.symbol, color = Sky, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
        }
        TextButton(onClick = onUpdates, contentPadding = PaddingValues(horizontal = 8.dp)) {
            Text("MAJ", fontSize = 11.sp)
        }
        if (state.session != null) {
            TextButton(onClick = onLogout, contentPadding = PaddingValues(horizontal = 8.dp)) {
                Text("Déconnexion", fontSize = 11.sp)
            }
        }
    }
}

@Composable
private fun MessageBanner(message: String, isError: Boolean, onDismiss: () -> Unit) {
    val accent = if (isError) Red else Green
    Row(
        Modifier.fillMaxWidth()
            .padding(bottom = 8.dp)
            .background(accent.copy(alpha = 0.12f), RoundedCornerShape(10.dp))
            .padding(start = 12.dp, end = 4.dp, top = 8.dp, bottom = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(message, Modifier.weight(1f), color = accent, fontSize = 12.sp)
        TextButton(onClick = onDismiss, contentPadding = PaddingValues(4.dp)) {
            Text("OK", color = accent, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
private fun LoginPanel(
    state: UiState,
    onConnect: (String, String, Boolean) -> Unit,
    onUpdates: () -> Unit,
) {
    var email by rememberSaveable { mutableStateOf(state.email) }
    var password by rememberSaveable { mutableStateOf("") }
    var motDePasseVisible by rememberSaveable { mutableStateOf(false) }
    var remember by rememberSaveable { mutableStateOf(state.email.isNotBlank()) }

    Column(
        Modifier.fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(bottom = 24.dp),
    ) {
        Card(
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = CardColor),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(Modifier.padding(18.dp)) {
                Text("Connexion Blink", fontSize = 18.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(4.dp))
                Text(
                    "Utilisez votre compte Blink habituel. L'authentification passe par l'API officielle (OAuth 2 + code 2FA).",
                    fontSize = 12.sp,
                    color = Muted,
                )
                Spacer(Modifier.height(16.dp))
                OutlinedTextField(
                    value = email,
                    onValueChange = { email = it },
                    label = { Text("Email Blink") },
                    leadingIcon = { Icon(Icons.Rounded.Email, contentDescription = null) },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(10.dp))
                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    label = { Text("Mot de passe") },
                    leadingIcon = { Icon(Icons.Rounded.Lock, contentDescription = null) },
                    trailingIcon = {
                        TextButton(
                            onClick = { motDePasseVisible = !motDePasseVisible },
                            contentPadding = PaddingValues(horizontal = 6.dp),
                        ) {
                            Text(
                                if (motDePasseVisible) "Masquer" else "Afficher",
                                fontSize = 10.sp,
                            )
                        }
                    },
                    singleLine = true,
                    visualTransformation = if (motDePasseVisible) {
                        VisualTransformation.None
                    } else {
                        PasswordVisualTransformation()
                    },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                    modifier = Modifier.fillMaxWidth(),
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(
                        checked = remember,
                        onCheckedChange = { remember = it },
                        colors = CheckboxDefaults.colors(checkedColor = Sky, uncheckedColor = Muted),
                    )
                    Text("Mémoriser l'email", fontSize = 12.sp, color = Muted)
                }
                Spacer(Modifier.height(8.dp))
                Button(
                    onClick = { onConnect(email, password, remember) },
                    enabled = !state.busy,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = Sky, contentColor = DarkOnSky),
                ) {
                    Text(if (state.busy) "Connexion…" else "Se connecter", fontWeight = FontWeight.SemiBold)
                }
                Spacer(Modifier.height(10.dp))
                Text(
                    "Le mot de passe n'est jamais enregistré sur l'appareil ; seul le jeton Blink est conservé.",
                    fontSize = 10.sp,
                    color = Muted,
                )
            }
        }
        Spacer(Modifier.height(12.dp))
        InfoCard(
            "🔒 Connexion sécurisée",
            "OAuth 2 avec PKCE et vérification 2FA, directement sur l'API officielle Blink. Aucun mot de passe stocké.",
        )
        Spacer(Modifier.height(10.dp))
        InfoCard(
            "🌡️ Relevés sans réveil",
            "Les températures sont lues passivement sur l'écran d'accueil Blink : les piles des caméras ne sont pas sollicitées.",
        )
        Spacer(Modifier.height(10.dp))
        InfoCard(
            "☑️ Sélection des caméras",
            "Après connexion, cochez les caméras à traiter. Seules celles-ci sont relevées, enregistrées et affichées.",
        )
        Spacer(Modifier.height(6.dp))
        TextButton(onClick = onUpdates, modifier = Modifier.fillMaxWidth()) {
            Text("Mises à jour", fontSize = 12.sp)
        }
    }
}

@Composable
private fun InfoCard(title: String, body: String) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = CardSoft),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(14.dp)) {
            Text(title, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = Sky)
            Spacer(Modifier.height(4.dp))
            Text(body, fontSize = 12.sp, color = Muted)
        }
    }
}

@Composable
private fun Dashboard(
    state: UiState,
    onRefresh: () -> Unit,
    onToggleCamera: (String) -> Unit,
    onSelectAll: () -> Unit,
    onSelectNone: () -> Unit,
    onToggleWakeCameras: () -> Unit,
    onWindowChange: (Int) -> Unit,
    onClearHistory: () -> Unit,
    onUpdates: () -> Unit,
) {
    val now = remember(state.readings, state.windowHours, state.lastSync) { System.currentTimeMillis() }
    val windowStart = now - state.windowHours * 3_600_000L
    val camerasCochees = state.cameras.filter { it.name in state.selected }

    val latestParCamera = remember(state.readings) {
        state.readings.groupBy { it.cameraName }
            .mapValues { (_, mesures) -> mesures.maxByOrNull { it.timestamp } }
    }
    val couleurs = remember(state.selected) {
        state.selected.sorted()
            .mapIndexed { index, nom -> nom to CameraPalette[index % CameraPalette.size] }
            .toMap()
    }
    val mesuresFenetre = remember(state.readings, state.selected, windowStart) {
        state.readings.filter {
            it.cameraName in state.selected && it.timestamp >= windowStart && it.tempC != null
        }
    }
    val stats = remember(mesuresFenetre) {
        mesuresFenetre.groupBy { it.cameraName }.mapValues { (_, mesures) ->
            val temperatures = mesures.mapNotNull { it.tempC }
            CameraStats(temperatures.size, temperatures.min(), temperatures.average(), temperatures.max())
        }
    }
    val series = remember(mesuresFenetre, couleurs) {
        mesuresFenetre.groupBy { it.cameraName }
            .map { (nom, mesures) ->
                CameraSeries(
                    nom,
                    mesures.sortedBy { it.timestamp }.map { it.timestamp to (it.tempC ?: 0.0) },
                    couleurs[nom] ?: Sky,
                )
            }
            .sortedBy { it.name }
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(10.dp),
        contentPadding = PaddingValues(bottom = 26.dp),
    ) {
        item { SyncBar(state, onRefresh) }
        item { CameraSelectionCard(state, onToggleCamera, onSelectAll, onSelectNone, onToggleWakeCameras) }
        item { SectionTitle("Dernières mesures") }

        when {
            state.selected.isEmpty() -> item {
                EmptyCard("Aucune caméra cochée. Cochez au moins une caméra pour lancer un relevé.")
            }

            camerasCochees.isEmpty() -> item {
                EmptyCard("Caméras en cours de découverte : lancez un relevé pour les charger.")
            }

            else -> items(camerasCochees.size, key = { camerasCochees[it].name }) { index ->
                val camera = camerasCochees[index]
                CameraCard(camera, latestParCamera[camera.name], state.unit)
            }
        }

        item { StatsCard(state, stats, series, windowStart, now, onWindowChange) }
        item { FooterCard(state, onClearHistory, onUpdates) }
    }
}

@Composable
private fun SyncBar(state: UiState, onRefresh: () -> Unit) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = CardColor),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(
                    if (state.lastSync != null) "Dernier relevé : ${formatDateTime(state.lastSync)}"
                    else "Aucun relevé pour l'instant",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium,
                )
                Spacer(Modifier.height(2.dp))
                Text(
                    "${state.selected.size} caméra(s) sélectionnée(s) · " +
                        "${state.readings.count { it.cameraName in state.selected }} mesure(s) en historique",
                    fontSize = 11.sp,
                    color = Muted,
                )
                Spacer(Modifier.height(2.dp))
                Text(
                    "Relevé automatique en arrière-plan : environ toutes les 15 min.",
                    fontSize = 11.sp,
                    color = Muted,
                )
            }
            Spacer(Modifier.width(8.dp))
            Button(
                onClick = onRefresh,
                enabled = !state.busy,
                colors = ButtonDefaults.buttonColors(containerColor = Sky, contentColor = DarkOnSky),
            ) {
                Icon(Icons.Rounded.Refresh, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(Modifier.width(6.dp))
                Text("Relever", fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
            }
        }
    }
}

@Composable
private fun CameraSelectionCard(
    state: UiState,
    onToggle: (String) -> Unit,
    onAll: () -> Unit,
    onNone: () -> Unit,
    onToggleWake: () -> Unit,
) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = CardColor),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Caméras à traiter", fontSize = 15.sp, fontWeight = FontWeight.Bold)
                    Text("Seules les caméras cochées sont relevées et affichées.", fontSize = 11.sp, color = Muted)
                }
                TextButton(onClick = onAll) { Text("Tout", fontSize = 12.sp) }
                TextButton(onClick = onNone) { Text("Rien", fontSize = 12.sp) }
            }

            if (state.cameras.isEmpty()) {
                Spacer(Modifier.height(6.dp))
                Text(
                    "Aucune caméra connue pour l'instant. Lancez un premier relevé : toutes seront sélectionnées par défaut.",
                    fontSize = 12.sp,
                    color = Muted,
                )
            } else {
                HorizontalDivider(color = Border, modifier = Modifier.padding(vertical = 6.dp))
                state.cameras.forEach { camera ->
                    val cochee = camera.name in state.selected
                    Row(
                        Modifier.fillMaxWidth()
                            .clickable { onToggle(camera.name) }
                            .padding(vertical = 3.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Checkbox(
                            checked = cochee,
                            onCheckedChange = { onToggle(camera.name) },
                            colors = CheckboxDefaults.colors(checkedColor = Sky, uncheckedColor = Muted),
                        )
                        Column(Modifier.weight(1f)) {
                            Text(
                                camera.name,
                                fontSize = 14.sp,
                                color = if (cochee) TextMain else Muted,
                                fontWeight = if (cochee) FontWeight.SemiBold else FontWeight.Normal,
                            )
                            Text(
                                listOfNotNull(
                                    camera.model,
                                    if (camera.outdoor) "Extérieur" else "Intérieur",
                                ).joinToString(" · "),
                                fontSize = 11.sp,
                                color = Muted,
                            )
                        }
                        camera.tempC?.let {
                            Text(
                                state.unit.format(it),
                                fontSize = 13.sp,
                                color = Sky,
                                fontWeight = FontWeight.Medium,
                            )
                        }
                    }
                }
            }

            HorizontalDivider(color = Border, modifier = Modifier.padding(vertical = 6.dp))
            Row(
                Modifier.fillMaxWidth()
                    .clickable { onToggleWake() }
                    .padding(vertical = 3.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Checkbox(
                    checked = state.wakeCameras,
                    onCheckedChange = { onToggleWake() },
                    colors = CheckboxDefaults.colors(checkedColor = Sky, uncheckedColor = Muted),
                )
                Column(Modifier.weight(1f)) {
                    Text(
                        "Réveiller les caméras si la température n'a pas changé",
                        fontSize = 13.sp,
                        color = if (state.wakeCameras) TextMain else Muted,
                        fontWeight = if (state.wakeCameras) FontWeight.SemiBold else FontWeight.Normal,
                    )
                    Text(
                        "Prend une photo, consomme la pile et peut durer une minute par caméra. " +
                            "En arrière-plan : au plus une fois par heure.",
                        fontSize = 10.sp,
                        color = Muted,
                    )
                }
            }
        }
    }
}

@Composable
private fun CameraCard(camera: CameraInfo, reading: Reading?, unit: TemperatureUnit) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = CardColor),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.Top) {
                Column(Modifier.weight(1f)) {
                    Text(camera.name, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                    Text(camera.model, fontSize = 11.sp, color = Muted)
                }
                Badge(
                    if (camera.outdoor) "Extérieur" else "Intérieur",
                    Muted,
                    Border.copy(alpha = 0.55f),
                )
            }
            Spacer(Modifier.height(4.dp))
            Text(
                unit.format(reading?.tempC),
                fontSize = 36.sp,
                fontWeight = FontWeight.Bold,
                color = Sky,
            )
            Spacer(Modifier.height(6.dp))

            val statut = reading?.status ?: camera.status
            val enLigne = statut != "offline"
            val pile = reading?.battery ?: camera.battery
            val pileFaible = pile == "low"
            val wifi = reading?.wifi ?: camera.wifi

            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Badge(
                    if (enLigne) "● En ligne" else "● Hors ligne",
                    if (enLigne) Green else Muted,
                )
                Badge(
                    if (pileFaible) "🪫 Pile faible" else "🔋 Pile OK",
                    if (pileFaible) Orange else Green,
                )
                if (wifi != null && wifi > 0) {
                    Badge("📶 Wi-Fi $wifi", Muted, Border.copy(alpha = 0.55f))
                }
            }

            HorizontalDivider(color = Border, modifier = Modifier.padding(vertical = 10.dp))
            if (reading != null) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("Dernier relevé : ${formatTime(reading.timestamp)}", fontSize = 11.sp, color = Muted)
                    Text("Date : ${formatDate(reading.timestamp)}", fontSize = 11.sp, color = Muted)
                }
            } else {
                Text("Aucune mesure enregistrée pour cette caméra.", fontSize = 11.sp, color = Muted)
            }
        }
    }
}

@Composable
private fun StatsCard(
    state: UiState,
    stats: Map<String, CameraStats>,
    series: List<CameraSeries>,
    since: Long,
    until: Long,
    onWindowChange: (Int) -> Unit,
) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = CardColor),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(14.dp)) {
            Text("Statistiques", fontSize = 15.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf(6 to "6 h", 24 to "24 h", 168 to "7 j").forEach { (heures, libelle) ->
                    WindowChip(libelle, state.windowHours == heures) { onWindowChange(heures) }
                }
            }
            Spacer(Modifier.height(10.dp))

            if (series.isEmpty()) {
                Text("Pas encore de mesure sur cette période.", fontSize = 12.sp, color = Muted)
            } else {
                TemperatureChart(
                    series = series,
                    unit = state.unit,
                    since = since,
                    until = until,
                    windowHours = state.windowHours,
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(8.dp))
                series.forEach { serie ->
                    Row(Modifier.padding(vertical = 2.dp), verticalAlignment = Alignment.CenterVertically) {
                        Box(Modifier.size(8.dp).background(serie.color, RoundedCornerShape(50)))
                        Spacer(Modifier.width(6.dp))
                        Text(
                            serie.name,
                            fontSize = 11.sp,
                            color = Muted,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.weight(1f),
                        )
                        Text("${stats[serie.name]?.count ?: 0} mes.", fontSize = 10.sp, color = Muted)
                    }
                }

                Spacer(Modifier.height(8.dp))
                HorizontalDivider(color = Border)
                Row(Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
                    Text("Caméra", Modifier.weight(1.5f), fontSize = 10.sp, color = Muted)
                    Text("Min", Modifier.weight(1f), fontSize = 10.sp, color = Muted, textAlign = TextAlign.End)
                    Text("Moy.", Modifier.weight(1f), fontSize = 10.sp, color = Muted, textAlign = TextAlign.End)
                    Text("Max", Modifier.weight(1f), fontSize = 10.sp, color = Muted, textAlign = TextAlign.End)
                }
                series.forEach { serie ->
                    val valeur = stats[serie.name]
                    Row(Modifier.fillMaxWidth().padding(vertical = 3.dp)) {
                        Text(
                            serie.name,
                            Modifier.weight(1.5f),
                            fontSize = 11.sp,
                            color = TextMain,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        Text(
                            state.unit.format(valeur?.minC),
                            Modifier.weight(1f),
                            fontSize = 11.sp,
                            color = Green,
                            textAlign = TextAlign.End,
                        )
                        Text(
                            state.unit.format(valeur?.avgC),
                            Modifier.weight(1f),
                            fontSize = 11.sp,
                            color = TextMain,
                            textAlign = TextAlign.End,
                        )
                        Text(
                            state.unit.format(valeur?.maxC),
                            Modifier.weight(1f),
                            fontSize = 11.sp,
                            color = Orange,
                            textAlign = TextAlign.End,
                        )
                    }
                }
            }
        }
    }
}

private data class CameraSeries(
    val name: String,
    val points: List<Pair<Long, Double>>,
    val color: Color,
)

@Composable
private fun TemperatureChart(
    series: List<CameraSeries>,
    unit: TemperatureUnit,
    since: Long,
    until: Long,
    windowHours: Int,
    modifier: Modifier,
) {
    val valeurs = series.flatMap { serie -> serie.points.mapNotNull { unit.fromCelsius(it.second) } }
    if (valeurs.isEmpty()) return

    // Fenêtre visible : elle suit la fenêtre complète tant que l'utilisateur
    // n'a pas zoomé, puis reste fixe lors des relevés suivants.
    var vueDebut by remember(windowHours) { mutableStateOf(since) }
    var vueFin by remember(windowHours) { mutableStateOf(until) }
    var fenetreComplete by remember(windowHours) { mutableStateOf(since to until) }

    LaunchedEffect(since, until) {
        val (ancienDebut, ancienFin) = fenetreComplete
        val etaitComplete = vueDebut <= ancienDebut + 1_000L && vueFin >= ancienFin - 1_000L
        if (etaitComplete) {
            vueDebut = since
            vueFin = until
        } else {
            val debut = vueDebut.coerceAtLeast(since)
            val fin = vueFin.coerceAtMost(until)
            if (fin - debut >= 60_000L) {
                vueDebut = debut
                vueFin = fin
            } else {
                vueDebut = since
                vueFin = until
            }
        }
        fenetreComplete = since to until
    }

    val dureeComplete = (until - since).coerceAtLeast(1L)
    val debut = vueDebut.coerceIn(since, until - 1L)
    val fin = vueFin.coerceIn(debut + 1L, until)
    val zoomed = fin - debut < dureeComplete

    val densite = LocalDensity.current
    val margeGauche = with(densite) { 48.dp.toPx() }
    val margeDroite = with(densite) { 4.dp.toPx() }
    var largeurPx by remember { mutableStateOf(0f) }
    val textMeasurer = rememberTextMeasurer()
    val styleAxe = TextStyle(color = Muted, fontSize = 9.sp)

    Column(modifier) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                if (zoomed) {
                    "Vue zoomée · pincer pour ajuster, glisser pour déplacer"
                } else {
                    "Pincer pour zoomer · glisser pour déplacer · double-tap pour tout afficher"
                },
                modifier = Modifier.weight(1f),
                fontSize = 10.sp,
                color = Muted,
            )
            if (zoomed) {
                Text(
                    "Réinitialiser",
                    modifier = Modifier
                        .clickable {
                            vueDebut = since
                            vueFin = until
                        }
                        .padding(horizontal = 6.dp, vertical = 4.dp),
                    fontSize = 10.sp,
                    color = Sky,
                    fontWeight = FontWeight.SemiBold,
                )
            }
        }

        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .height(170.dp)
                .onSizeChanged { largeurPx = it.width.toFloat() }
                .pointerInput(since, until, windowHours, largeurPx) {
                    val largeurTrace = (largeurPx - margeGauche - margeDroite).coerceAtLeast(1f)
                    detectTransformGestures(panZoomLock = true) { centroid, pan, zoom, _ ->
                        val span = (vueFin - vueDebut).coerceAtLeast(1L)
                        val fraction = ((centroid.x - margeGauche) / largeurTrace).coerceIn(0f, 1f)
                        val spanMin = minOf(dureeComplete, 10 * 60_000L)
                        val nouveauSpan = (span / zoom.coerceAtLeast(0.01f))
                            .toLong()
                            .coerceIn(spanMin, dureeComplete)
                        val ancre = vueDebut + (fraction * span).toLong()
                        val decalage = (-pan.x / largeurTrace * span).toLong()

                        var nouveauDebut = ancre - (fraction * nouveauSpan).toLong() + decalage
                        var nouvelleFin = nouveauDebut + nouveauSpan
                        if (nouveauDebut < since) {
                            nouveauDebut = since
                            nouvelleFin = since + nouveauSpan
                        }
                        if (nouvelleFin > until) {
                            nouvelleFin = until
                            nouveauDebut = until - nouveauSpan
                        }
                        vueDebut = nouveauDebut.coerceIn(since, until - 1L)
                        vueFin = nouvelleFin.coerceIn(vueDebut + 1L, until)
                    }
                }
                .pointerInput(since, until, windowHours) {
                    detectTapGestures(
                        onDoubleTap = {
                            vueDebut = since
                            vueFin = until
                        },
                    )
                }
        ) {
            val gauche = margeGauche
            val droite = size.width - margeDroite
            val haut = 6.dp.toPx()
            val bas = size.height - 20.dp.toPx()
            val largeurTrace = (droite - gauche).coerceAtLeast(1f)
            val hauteurTrace = (bas - haut).coerceAtLeast(1f)
            val duree = (fin - debut).coerceAtLeast(1L)

            val fenetre = series.flatMap { serie ->
                serie.points.mapNotNull { (horodatage, tempC) ->
                    if (horodatage in debut..fin) unit.fromCelsius(tempC) else null
                }
            }
            var minV = fenetre.minOrNull() ?: 0.0
            var maxV = fenetre.maxOrNull() ?: 30.0
            if (maxV - minV < 0.5) {
                minV -= 0.5
                maxV += 0.5
            }
            val marge = (maxV - minV) * 0.12
            minV -= marge
            maxV += marge

            val pas = niceStep((maxV - minV) / 4.0)
            val grilleBas = floor(minV / pas) * pas
            val grilleHaut = ceil(maxV / pas) * pas
            val amplitude = (grilleHaut - grilleBas).coerceAtLeast(0.001)

            // Graduations horizontales avec valeurs de température.
            var indexY = 0
            while (grilleBas + indexY * pas <= grilleHaut + pas / 2 && indexY < 12) {
                val valeur = grilleBas + indexY * pas
                val y = haut + hauteurTrace -
                    ((valeur - grilleBas) / amplitude * hauteurTrace).toFloat()
                drawLine(
                    color = Border,
                    start = Offset(gauche, y),
                    end = Offset(droite, y),
                    strokeWidth = 1f,
                    pathEffect = PathEffect.dashPathEffect(floatArrayOf(4f, 4f)),
                )
                val texte = Temperature.formatValue(valeur) + unit.symbol
                val mise = textMeasurer.measure(texte, styleAxe)
                drawText(
                    textLayoutResult = mise,
                    topLeft = Offset(
                        gauche - 6.dp.toPx() - mise.size.width,
                        y - mise.size.height / 2f,
                    ),
                )
                indexY += 1
            }

            // Graduations verticales avec dates et heures.
            val nbX = (largeurTrace / 92.dp.toPx()).toInt().coerceIn(3, 6)
            for (index in 0..nbX) {
                val fraction = index / nbX.toFloat()
                val x = gauche + fraction * largeurTrace
                val temps = debut + (fraction * duree).toLong()
                drawLine(
                    color = Border,
                    start = Offset(x, haut),
                    end = Offset(x, bas),
                    strokeWidth = 1f,
                    pathEffect = PathEffect.dashPathEffect(floatArrayOf(4f, 4f)),
                )
                drawLine(
                    color = Muted,
                    start = Offset(x, bas),
                    end = Offset(x, bas + 4.dp.toPx()),
                    strokeWidth = 1f,
                )
                val mise = textMeasurer.measure(formaterAxeTemps(temps, duree), styleAxe)
                val xTexte = (x - mise.size.width / 2f)
                    .coerceIn(gauche, size.width - mise.size.width)
                drawText(
                    textLayoutResult = mise,
                    topLeft = Offset(xTexte, bas + 6.dp.toPx()),
                )
            }

            if (fenetre.isEmpty()) {
                val mise = textMeasurer.measure(
                    "Aucune mesure sur cette plage",
                    TextStyle(color = Muted, fontSize = 11.sp),
                )
                drawText(
                    textLayoutResult = mise,
                    topLeft = Offset(
                        gauche + (largeurTrace - mise.size.width) / 2f,
                        haut + (hauteurTrace - mise.size.height) / 2f,
                    ),
                )
                return@Canvas
            }

            for (serie in series) {
                val points = serie.points.mapNotNull { (horodatage, tempC) ->
                    if (horodatage !in debut..fin) return@mapNotNull null
                    val valeur = unit.fromCelsius(tempC) ?: return@mapNotNull null
                    val x = gauche +
                        ((horodatage - debut).toFloat() / duree) * largeurTrace
                    val y = haut + hauteurTrace -
                        ((valeur - grilleBas) / amplitude * hauteurTrace).toFloat()
                    Offset(x, y)
                }
                when {
                    points.size == 1 -> drawCircle(
                        serie.color,
                        radius = 3.dp.toPx(),
                        center = points.first(),
                    )
                    points.size > 1 -> {
                        val chemin = Path().apply {
                            moveTo(points.first().x, points.first().y)
                            for (point in points.drop(1)) lineTo(point.x, point.y)
                        }
                        drawPath(
                            chemin,
                            serie.color,
                            style = Stroke(
                                width = 2.dp.toPx(),
                                cap = StrokeCap.Round,
                                join = StrokeJoin.Round,
                            ),
                        )
                    }
                }
            }
        }
    }
}

/** Pas « rond » (1, 2 ou 5 × 10ⁿ) pour des graduations lisibles. */
private fun niceStep(brut: Double): Double {
    if (!brut.isFinite() || brut <= 0.0) return 1.0
    val exposant = floor(log10(brut))
    val base = 10.0.pow(exposant)
    val fraction = brut / base
    val pas = when {
        fraction <= 1.0 -> 1.0
        fraction <= 2.0 -> 2.0
        fraction <= 5.0 -> 5.0
        else -> 10.0
    }
    return pas * base
}

/** Format des dates de l'axe horizontal, adapté à la durée affichée. */
private fun formaterAxeTemps(timestamp: Long, dureeMs: Long): String {
    val date = Instant.ofEpochMilli(timestamp).atZone(ZoneId.systemDefault())
    val motif = when {
        dureeMs > 7L * 86_400_000L -> "dd/MM"
        dureeMs > 36L * 3_600_000L -> "dd/MM HH'h'"
        dureeMs > 10L * 60_000L -> "HH:mm"
        else -> "HH:mm:ss"
    }
    return DateTimeFormatter.ofPattern(motif, Locale.FRENCH).format(date)
}

@Composable
private fun WindowChip(label: String, selected: Boolean, onClick: () -> Unit) {
    Box(
        Modifier
            .background(if (selected) Sky else Color(0xFF172033), RoundedCornerShape(50))
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 6.dp),
    ) {
        Text(
            label,
            fontSize = 12.sp,
            color = if (selected) DarkOnSky else Muted,
            fontWeight = FontWeight.SemiBold,
        )
    }
}

@Composable
private fun FooterCard(state: UiState, onClearHistory: () -> Unit, onUpdates: () -> Unit) {
    var confirmation by remember { mutableStateOf(false) }

    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = CardSoft),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(14.dp)) {
            Text("Historique local", fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(4.dp))
            Text(
                "${state.readings.size} mesure(s) conservée(s) sur 30 jours (plafond 5000). " +
                    "Fichier privé à l'application.",
                fontSize = 11.sp,
                color = Muted,
            )
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(
                    onClick = onUpdates,
                ) {
                    Text("Mises à jour", fontSize = 12.sp)
                }
                OutlinedButton(
                    onClick = { confirmation = true },
                    enabled = state.readings.isNotEmpty(),
                ) {
                    Text("Effacer l'historique", fontSize = 12.sp)
                }
            }
        }
    }

    if (confirmation) {
        AlertDialog(
            onDismissRequest = { confirmation = false },
            containerColor = CardColor,
            title = { Text("Effacer l'historique ?") },
            text = {
                Text(
                    "Toutes les mesures enregistrées sur cet appareil seront supprimées. " +
                        "La session Blink et les caméras sélectionnées sont conservées.",
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    confirmation = false
                    onClearHistory()
                }) { Text("Effacer", color = Red) }
            },
            dismissButton = {
                TextButton(onClick = { confirmation = false }) { Text("Annuler") }
            },
        )
    }
}

@Composable
private fun SectionTitle(title: String) {
    Text(title, fontSize = 15.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 4.dp))
}

@Composable
private fun EmptyCard(message: String) {
    Card(
        colors = CardDefaults.cardColors(containerColor = CardSoft),
        shape = RoundedCornerShape(14.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(message, Modifier.padding(16.dp), fontSize = 12.sp, color = Muted)
    }
}

@Composable
private fun Badge(text: String, foreground: Color, background: Color = foreground.copy(alpha = 0.14f)) {
    Box(
        Modifier.background(background, RoundedCornerShape(50))
            .padding(horizontal = 8.dp, vertical = 3.dp),
    ) {
        Text(text, fontSize = 10.sp, color = foreground, fontWeight = FontWeight.Medium)
    }
}

@Composable
private fun TwoFactorDialog(state: UiState, onSubmit: (String) -> Unit, onCancel: () -> Unit) {
    var code by rememberSaveable { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onCancel,
        containerColor = CardColor,
        title = { Text("Vérification 2FA") },
        text = {
            Column {
                Text(
                    "Saisissez le code de vérification envoyé par Blink (email ou SMS).",
                    fontSize = 13.sp,
                    color = Muted,
                )
                Spacer(Modifier.height(10.dp))
                OutlinedTextField(
                    value = code,
                    onValueChange = { saisie -> code = saisie.filter { it.isDigit() }.take(8) },
                    label = { Text("Code") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier.fillMaxWidth(),
                )
                state.twoFactorError?.let {
                    Spacer(Modifier.height(8.dp))
                    Text(it, fontSize = 11.sp, color = Red)
                }
            }
        },
        confirmButton = {
            TextButton(onClick = { onSubmit(code) }, enabled = !state.busy) { Text("Valider") }
        },
        dismissButton = {
            TextButton(onClick = onCancel, enabled = !state.busy) { Text("Annuler") }
        },
    )
}

@Composable
private fun BusyOverlay(label: String) {
    val interaction = remember { MutableInteractionSource() }
    Box(
        Modifier.fillMaxSize()
            .background(Color(0xCC0B1120))
            .clickable(interactionSource = interaction, indication = null) { },
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            CircularProgressIndicator(color = Sky)
            Spacer(Modifier.height(12.dp))
            Text(label, color = TextMain, fontSize = 13.sp)
        }
    }
}

private val HeureFormat = DateTimeFormatter.ofPattern("HH:mm", Locale.FRANCE)
private val DateFormat = DateTimeFormatter.ofPattern("dd/MM/yyyy", Locale.FRANCE)

private fun formatTime(timestamp: Long): String =
    Instant.ofEpochMilli(timestamp).atZone(ZoneId.systemDefault()).format(HeureFormat)

private fun formatDate(timestamp: Long): String =
    Instant.ofEpochMilli(timestamp).atZone(ZoneId.systemDefault()).format(DateFormat)

private fun formatDateTime(timestamp: Long): String = "${formatDate(timestamp)} ${formatTime(timestamp)}"
