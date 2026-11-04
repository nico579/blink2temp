package com.nico.blink2temp

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.nico.blink2temp.blink.BlinkAuthException
import com.nico.blink2temp.blink.BlinkClient
import com.nico.blink2temp.blink.BlinkSession
import com.nico.blink2temp.blink.CameraInfo
import com.nico.blink2temp.blink.LoginOutcome
import com.nico.blink2temp.core.Temperature
import com.nico.blink2temp.core.TemperatureUnit
import com.nico.blink2temp.data.MeasurementStore
import com.nico.blink2temp.data.Reading
import com.nico.blink2temp.data.SessionStore
import com.nico.blink2temp.sync.ReadingScheduler
import com.nico.blink2temp.sync.ReadingSync
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.util.Locale
import java.util.UUID

data class UiState(
    val unit: TemperatureUnit = TemperatureUnit.CELSIUS,
    val session: BlinkSession? = null,
    val email: String = "",
    val busy: Boolean = false,
    val busyLabel: String = "",
    val error: String? = null,
    val notice: String? = null,
    val awaitingTwoFactor: Boolean = false,
    val twoFactorError: String? = null,
    val cameras: List<CameraInfo> = emptyList(),
    val selected: Set<String> = emptySet(),
    val selectionInitialised: Boolean = false,
    val readings: List<Reading> = emptyList(),
    val lastSync: Long? = null,
    val windowHours: Int = 24,
    val wakeCameras: Boolean = false,
)

class AppViewModel(application: Application) : AndroidViewModel(application) {
    private val sessionStore = SessionStore(application)
    private val measurementStore = MeasurementStore(File(application.filesDir, "historique.json"))
    private val client = BlinkClient()

    private val _state = MutableStateFlow(
        UiState(
            unit = Temperature.unitFor(Locale.getDefault()),
        ),
    )
    val state: StateFlow<UiState> = _state.asStateFlow()

    init {
        val session = sessionStore.loadSession()
        val selection = sessionStore.loadSelection()
        val historique = measurementStore.load()
        _state.update {
            it.copy(
                session = session,
                email = sessionStore.loadEmail(),
                selected = selection.orEmpty(),
                selectionInitialised = selection != null,
                readings = historique,
                lastSync = historique.maxOfOrNull { mesure -> mesure.timestamp },
                wakeCameras = sessionStore.loadWakeCameras(),
            )
        }
        if (session != null) {
            ReadingScheduler.schedule(getApplication<Application>())
            lancer("Connexion à Blink…") { synchroniser() }
        } else {
            ReadingScheduler.cancel(getApplication<Application>())
        }
    }

    /** Connexion Blink (email + mot de passe), avec 2FA si le compte l'exige. */
    fun connect(email: String, password: String, rememberEmail: Boolean) {
        val mail = email.trim()
        if (mail.isBlank() || password.isEmpty()) {
            _state.update { it.copy(error = "Renseignez votre email et votre mot de passe.") }
            return
        }
        sessionStore.saveEmail(if (rememberEmail) mail else "")

        lancer("Connexion à Blink…") {
            val hardwareId = sessionStore.loadHardwareId()
                ?: UUID.randomUUID().toString().uppercase(Locale.ROOT)
                    .also { sessionStore.saveHardwareId(it) }

            when (val resultat = withContext(Dispatchers.IO) {
                client.login(mail, password, hardwareId)
            }) {
                is LoginOutcome.Success -> {
                    sessionStore.saveSession(resultat.session)
                    ReadingScheduler.schedule(getApplication<Application>())
                    _state.update {
                        it.copy(
                            session = resultat.session,
                            email = mail,
                            awaitingTwoFactor = false,
                            twoFactorError = null,
                            error = null,
                        )
                    }
                    synchroniser()
                }

                LoginOutcome.TwoFactorRequired -> _state.update {
                    it.copy(awaitingTwoFactor = true, twoFactorError = null)
                }

                is LoginOutcome.Failure -> _state.update { it.copy(error = resultat.message) }
            }
        }
    }

    fun submitTwoFactor(code: String) {
        val codeNettoye = code.trim()
        if (codeNettoye.isBlank()) {
            _state.update { it.copy(twoFactorError = "Saisissez le code reçu par email ou SMS.") }
            return
        }
        lancer("Vérification du code…") {
            when (val resultat = withContext(Dispatchers.IO) {
                client.submitTwoFactor(codeNettoye)
            }) {
                is LoginOutcome.Success -> {
                    sessionStore.saveSession(resultat.session)
                    ReadingScheduler.schedule(getApplication<Application>())
                    _state.update {
                        it.copy(
                            session = resultat.session,
                            awaitingTwoFactor = false,
                            twoFactorError = null,
                            error = null,
                        )
                    }
                    synchroniser()
                }

                LoginOutcome.TwoFactorRequired ->
                    _state.update { it.copy(twoFactorError = "Code supplémentaire requis.") }

                is LoginOutcome.Failure ->
                    _state.update { it.copy(twoFactorError = resultat.message) }
            }
        }
    }

    fun cancelTwoFactor() {
        client.cancelPendingLogin()
        _state.update { it.copy(awaitingTwoFactor = false, twoFactorError = null) }
    }

    /** Relevé manuel des caméras cochées. */
    fun relever() {
        val etat = _state.value
        if (etat.session == null) return
        if (etat.selectionInitialised && etat.selected.isEmpty()) {
            _state.update { it.copy(error = "Cochez au moins une caméra avant de lancer un relevé.") }
            return
        }
        lancer("Relevé des caméras sélectionnées…") { synchroniser(forcé = true) }
    }

    /** Active ou désactive le réveil des caméras avant chaque lecture. */
    fun toggleWakeCameras() {
        val actif = !_state.value.wakeCameras
        sessionStore.saveWakeCameras(actif)
        _state.update { it.copy(wakeCameras = actif) }
    }

    fun toggleCamera(name: String) {
        val selection = _state.value.selected.toMutableSet()
        if (!selection.add(name)) selection.remove(name)
        sessionStore.saveSelection(selection)
        _state.update { it.copy(selected = selection, selectionInitialised = true) }
    }

    fun selectAll() {
        val tous = _state.value.cameras.map { it.name }.toSet()
        sessionStore.saveSelection(tous)
        _state.update { it.copy(selected = tous, selectionInitialised = true) }
    }

    fun selectNone() {
        sessionStore.saveSelection(emptySet())
        _state.update { it.copy(selected = emptySet(), selectionInitialised = true) }
    }

    fun changeWindow(hours: Int) {
        _state.update { it.copy(windowHours = hours) }
    }

    /** Recharge l'historique écrit par le relevé automatique en arrière-plan. */
    fun reloadHistory() {
        val readings = measurementStore.load()
        _state.update { etat ->
            val dernier = listOfNotNull(
                etat.lastSync,
                readings.maxOfOrNull { mesure -> mesure.timestamp },
            ).maxOrNull()
            etat.copy(readings = readings, lastSync = dernier)
        }
    }

    fun logout() {
        client.cancelPendingLogin()
        ReadingScheduler.cancel(getApplication<Application>())
        sessionStore.clearSession()
        _state.update {
            it.copy(
                session = null,
                cameras = emptyList(),
                awaitingTwoFactor = false,
                twoFactorError = null,
                error = null,
                notice = "Déconnecté du compte Blink.",
            )
        }
    }

    fun clearHistory() {
        measurementStore.clear()
        _state.update {
            it.copy(readings = emptyList(), notice = "Historique local effacé.")
        }
    }

    fun dismissMessage() {
        _state.update { it.copy(error = null, notice = null) }
    }

    // ------------------------------------------------------------------ interne

    private fun lancer(label: String, block: suspend () -> Unit) {
        if (_state.value.busy) return
        viewModelScope.launch {
            _state.update { it.copy(busy = true, busyLabel = label, error = null, notice = null) }
            try {
                block()
            } catch (erreur: BlinkAuthException) {
                sessionStore.clearSession()
                _state.update {
                    it.copy(
                        session = null,
                        awaitingTwoFactor = false,
                        error = erreur.message ?: "Session Blink expirée.",
                    )
                }
            } catch (erreur: Exception) {
                _state.update { it.copy(error = messageLisible(erreur)) }
            } finally {
                _state.update { it.copy(busy = false, busyLabel = "") }
            }
        }
    }

    /**
     * Récupère l'écran d'accueil, ne conserve que les caméras cochées, puis
     * enregistre les mesures dans l'historique local.
     */
    private suspend fun synchroniser(forcé: Boolean = false) {
        val etat = _state.value
        val resultat = withContext(Dispatchers.IO) {
            ReadingSync.run(
                context = getApplication<Application>(),
                wake = etat.wakeCameras,
                respectWakeCooldown = !forcé,
            )
        } ?: run {
            if (_state.value.session == null) {
                throw BlinkAuthException("Connectez-vous à votre compte Blink.")
            }
            return
        }

        val avertissement = if (resultat.wakeFailures.isEmpty()) null else {
            "Réveil impossible pour : ${resultat.wakeFailures.joinToString(", ")}. " +
                "La température affichée peut être ancienne."
        }
        _state.update {
            it.copy(
                session = resultat.session,
                cameras = resultat.cameras,
                selected = resultat.selection,
                selectionInitialised = true,
                readings = resultat.readings,
                lastSync = resultat.timestamp,
                error = null,
                notice = avertissement,
            )
        }
    }

    private fun messageLisible(erreur: Exception): String = when (erreur) {
        is UnknownHostException -> "Impossible de joindre Blink (serveur introuvable). Vérifiez votre réseau puis réessayez."
        is SocketTimeoutException -> "Blink ne répond pas. Réessayez dans quelques instants."
        else -> erreur.message?.takeIf { it.isNotBlank() }
            ?: "Erreur inattendue (${erreur.javaClass.simpleName})."
    }
}
