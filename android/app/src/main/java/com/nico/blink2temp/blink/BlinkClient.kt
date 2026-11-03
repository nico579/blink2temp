package com.nico.blink2temp.blink

import org.json.JSONObject
import java.net.URLEncoder
import java.security.SecureRandom

class BlinkException(message: String, cause: Throwable? = null) : Exception(message, cause)

class BlinkAuthException(message: String) : Exception(message)

sealed class LoginOutcome {
    data class Success(val session: BlinkSession) : LoginOutcome()
    data object TwoFactorRequired : LoginOutcome()
    data class Failure(val message: String) : LoginOutcome()
}

/**
 * Client Blink natif : OAuth v2 (Authorization Code + PKCE), vérification 2FA,
 * rafraîchissement du jeton puis lecture passive de l'écran d'accueil.
 *
 * Le parcours reprend celui de blinkpy (auth.py / api.py) sans dépendance
 * Python ni OkHttp : HttpURLConnection et un bocal de cookies suffisent.
 */
class BlinkClient(
    private val transport: HttpTransport = HttpTransport(),
    private val random: SecureRandom = SecureRandom(),
) {
    private data class PendingLogin(
        val username: String,
        val hardwareId: String,
        val verifier: String,
        val csrfToken: String,
    )

    private var pendingLogin: PendingLogin? = null

    /** Étape 1 à 4 : connexion email / mot de passe. */
    fun login(username: String, password: String, hardwareId: String): LoginOutcome {
        pendingLogin = null
        transport.clearCookies()

        val verifier = Pkce.generateVerifier(random)
        val challenge = Pkce.challenge(verifier)
        val urlAutorisation = AUTHORIZE_URL + "?" + encoderQuery(
            mapOf(
                "app_brand" to "blink",
                "app_version" to "50.1",
                "client_id" to CLIENT_ID,
                "code_challenge" to challenge,
                "code_challenge_method" to "S256",
                "device_brand" to "Apple",
                "device_model" to "iPhone16,1",
                "device_os_version" to "26.1",
                "hardware_id" to hardwareId,
                "redirect_uri" to REDIRECT_URI,
                "response_type" to "code",
                "scope" to SCOPE,
            ),
        )

        val autorisation = transport.get(urlAutorisation, headers = navigateurEntetes())
        if (autorisation.status != 200) {
            return LoginOutcome.Failure("Blink a refusé l'accès (étape 1, code ${autorisation.status}).")
        }

        val pageConnexion = transport.get(SIGNIN_URL, headers = navigateurEntetes())
        val csrf = OAuthHtml.extractCsrfToken(pageConnexion.body)
            ?: return LoginOutcome.Failure(
                "Jeton de sécurité Blink introuvable (CSRF). Réessayez dans quelques instants.",
            )

        val enAttente = PendingLogin(username.trim(), hardwareId, verifier, csrf)
        val reponse = transport.postForm(
            SIGNIN_URL,
            mapOf("username" to enAttente.username, "password" to password, "csrf-token" to csrf),
            headers = formulaireEntetes(),
            followRedirects = false,
        )

        return when {
            reponse.status in 300..399 -> terminerConnexion(enAttente)

            reponse.status == 412 -> {
                pendingLogin = enAttente
                LoginOutcome.TwoFactorRequired
            }

            reponse.status == 202 -> {
                val json = reponse.json()
                val deuxFacteurs = json != null && (
                    json.champRenseigne("tsv_state") ||
                        json.champRenseigne("tsv_methods") ||
                        json.optLong("next_time_in_secs", 0L) > 0L
                    )
                if (deuxFacteurs) {
                    pendingLogin = enAttente
                    LoginOutcome.TwoFactorRequired
                } else {
                    LoginOutcome.Failure(
                        "Blink n'a pas accepté la connexion (code 202). Vérifiez vos identifiants.",
                    )
                }
            }

            reponse.status == 401 -> LoginOutcome.Failure("Email ou mot de passe incorrect.")
            reponse.status == 403 -> LoginOutcome.Failure(
                "Connexion bloquée par Blink. Validez une connexion dans l'application Blink, puis réessayez.",
            )

            else -> LoginOutcome.Failure("Connexion refusée par Blink (code ${reponse.status}).")
        }
    }

    /** Étape 4 bis : validation du code 2FA puis récupération des jetons. */
    fun submitTwoFactor(code: String): LoginOutcome {
        val enAttente = pendingLogin
            ?: return LoginOutcome.Failure("Session de connexion expirée : recommencez la connexion.")

        val reponse = transport.postForm(
            TWOFA_URL,
            mapOf(
                "2fa_code" to code.trim(),
                "csrf-token" to enAttente.csrfToken,
                "remember_me" to "false",
            ),
            headers = formulaireEntetes(),
        )

        if (reponse.status != 201) {
            return LoginOutcome.Failure("Code de vérification refusé (code ${reponse.status}).")
        }
        val statut = reponse.json()?.optString("status").orEmpty()
        if (statut != "auth-completed") {
            return LoginOutcome.Failure("Code de vérification refusé. Vérifiez le code et réessayez.")
        }
        return terminerConnexion(enAttente)
    }

    fun cancelPendingLogin() {
        pendingLogin = null
    }

    /** Rafraîchit l'accès à partir du refresh token ; lève BlinkAuthException si expiré. */
    fun refreshSession(session: BlinkSession): BlinkSession {
        val reponse = transport.postForm(
            TOKEN_URL,
            mapOf(
                "grant_type" to "refresh_token",
                "refresh_token" to session.refreshToken,
                "client_id" to CLIENT_ID,
                "scope" to SCOPE,
                "hardware_id" to session.hardwareId,
            ),
            headers = tokenEntetes(),
        )
        when (reponse.status) {
            200 -> Unit
            400, 401, 403 -> throw BlinkAuthException("Session Blink expirée : reconnectez-vous.")
            else -> throw BlinkException("Rafraîchissement du jeton impossible (code ${reponse.status}).")
        }
        return construireSession(reponse, session.username, session.hardwareId, session)
            ?: throw BlinkException("Réponse de rafraîchissement Blink illisible.")
    }

    /**
     * Lit l'écran d'accueil : interrogation passive qui ne réveille pas les caméras.
     */
    fun fetchCameras(session: BlinkSession): List<CameraInfo> {
        val url = "https://${session.host}/api/v3/accounts/${session.accountId}/homescreen"
        val reponse = transport.get(
            url,
            headers = mapOf(
                "Authorization" to "Bearer ${session.accessToken}",
                "Content-Type" to "application/json",
                "User-Agent" to API_USER_AGENT,
            ),
        )
        when (reponse.status) {
            200 -> Unit
            401, 403 -> throw BlinkAuthException("Session Blink expirée : reconnectez-vous.")
            else -> throw BlinkException("Écran d'accueil Blink indisponible (code ${reponse.status}).")
        }
        return try {
            parseHomescreen(reponse.body)
        } catch (erreur: Exception) {
            throw BlinkException("Réponse Blink illisible.", erreur)
        }
    }

    private fun terminerConnexion(enAttente: PendingLogin): LoginOutcome {
        val autorisation = transport.get(
            AUTHORIZE_URL,
            headers = navigateurEntetes(mapOf("Referer" to SIGNIN_URL)),
            followRedirects = false,
        )
        if (autorisation.status !in 300..399) {
            return LoginOutcome.Failure(
                "Blink n'a pas renvoyé de code d'autorisation (code ${autorisation.status}).",
            )
        }
        val code = OAuthHtml.extractAuthorizationCode(autorisation.header("location"))
            ?: return LoginOutcome.Failure("Code d'autorisation absent de la réponse Blink.")

        val jeton = transport.postForm(
            TOKEN_URL,
            mapOf(
                "app_brand" to "blink",
                "client_id" to CLIENT_ID,
                "code" to code,
                "code_verifier" to enAttente.verifier,
                "grant_type" to "authorization_code",
                "hardware_id" to enAttente.hardwareId,
                "redirect_uri" to REDIRECT_URI,
                "scope" to SCOPE,
            ),
            headers = tokenEntetes(),
        )
        if (jeton.status != 200) {
            return LoginOutcome.Failure("Blink a refusé l'échange du jeton (code ${jeton.status}).")
        }

        val session = construireSession(jeton, enAttente.username, enAttente.hardwareId, null)
            ?: return LoginOutcome.Failure("Réponse de jeton Blink illisible. Réessayez.")
        pendingLogin = null
        return LoginOutcome.Success(session)
    }

    private fun construireSession(
        reponse: HttpResponse,
        username: String,
        hardwareId: String,
        existante: BlinkSession?,
    ): BlinkSession? {
        val json = reponse.json() ?: return null
        val accessToken = json.optString("access_token").trim()
        if (accessToken.isEmpty()) return null

        val refreshToken = json.optString("refresh_token").trim()
            .ifEmpty { existante?.refreshToken ?: return null }
        val expiresIn = json.optLong("expires_in", 3_600L)
            .coerceIn(60L, 7L * 24L * 3_600L)

        val hote: String
        val compte: String
        if (existante != null) {
            hote = existante.host
            compte = existante.accountId
        } else {
            val infos = infosTier(accessToken) ?: return null
            hote = infos.first
            compte = infos.second
        }

        return BlinkSession(
            username = username,
            hardwareId = hardwareId,
            accessToken = accessToken,
            refreshToken = refreshToken,
            expiresAt = System.currentTimeMillis() + expiresIn * 1_000L,
            host = hote,
            accountId = compte,
        )
    }

    /** Récupère la région (tier) et l'identifiant de compte via tier_info. */
    private fun infosTier(accessToken: String): Pair<String, String>? {
        val reponse = transport.get(
            TIER_URL,
            headers = mapOf(
                "Authorization" to "Bearer $accessToken",
                "Content-Type" to "application/x-www-form-urlencoded",
                "User-Agent" to API_USER_AGENT,
            ),
        )
        if (reponse.status != 200) return null
        val json = reponse.json() ?: return null
        val tier = json.optString("tier").trim()
        val compte = json.opt("account_id")?.toString()?.trim()
        if (tier.isEmpty() || compte.isNullOrEmpty() || compte == "null") return null
        return "$tier.immedia-semi.com" to compte
    }

    private fun navigateurEntetes(extra: Map<String, String> = emptyMap()): Map<String, String> =
        mapOf(
            "User-Agent" to OAUTH_USER_AGENT,
            "Accept" to "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        ) + extra

    private fun formulaireEntetes(): Map<String, String> = mapOf(
        "User-Agent" to OAUTH_USER_AGENT,
        "Accept" to "*/*",
        "Origin" to OAUTH_BASE,
        "Referer" to SIGNIN_URL,
    )

    private fun tokenEntetes(): Map<String, String> = mapOf(
        "User-Agent" to TOKEN_USER_AGENT,
        "Accept" to "*/*",
    )

    private fun encoderQuery(parametres: Map<String, String>): String =
        parametres.entries.joinToString("&") { (cle, valeur) ->
            "${URLEncoder.encode(cle, "UTF-8")}=${URLEncoder.encode(valeur, "UTF-8")}"
        }

    private fun JSONObject.champRenseigne(cle: String): Boolean = when (val valeur = opt(cle)) {
        null, JSONObject.NULL -> false
        is String -> valeur.isNotBlank()
        is Boolean -> valeur
        is Number -> valeur.toDouble() != 0.0
        is org.json.JSONArray -> valeur.length() > 0
        else -> true
    }

    private companion object {
        const val OAUTH_BASE = "https://api.oauth.blink.com"
        const val AUTHORIZE_URL = "$OAUTH_BASE/oauth/v2/authorize"
        const val SIGNIN_URL = "$OAUTH_BASE/oauth/v2/signin"
        const val TWOFA_URL = "$OAUTH_BASE/oauth/v2/2fa/verify"
        const val TOKEN_URL = "$OAUTH_BASE/oauth/token"
        const val TIER_URL = "https://rest-prod.immedia-semi.com/api/v1/users/tier_info"

        const val CLIENT_ID = "ios"
        const val SCOPE = "client"
        const val REDIRECT_URI = "immedia-blink://applinks.blink.com/signin/callback"

        const val OAUTH_USER_AGENT =
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) " +
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.1 Mobile/15E148 Safari/604.1"
        const val TOKEN_USER_AGENT = "Blink/2511191620 CFNetwork/3860.200.71 Darwin/25.1.0"
        const val API_USER_AGENT = "27.0ANDROID_28373244"
    }
}
