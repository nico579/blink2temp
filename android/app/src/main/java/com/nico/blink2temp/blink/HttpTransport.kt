package com.nico.blink2temp.blink

import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.nio.charset.StandardCharsets

/** Réponse HTTP brute, en-têtes normalisés en minuscules. */
data class HttpResponse(
    val status: Int,
    val headers: Map<String, String>,
    val body: String,
) {
    fun header(nom: String): String? = headers[nom.lowercase()]

    fun json(): JSONObject? = try {
        JSONObject(body)
    } catch (_: Exception) {
        null
    }
}

/**
 * Transport HTTP minimal basé sur HttpURLConnection (aucune dépendance externe)
 * avec un bocal de cookies en mémoire, nécessaire au parcours OAuth Blink.
 */
class HttpTransport(
    private val connectTimeoutMs: Int = 20_000,
    private val readTimeoutMs: Int = 30_000,
) {
    private companion object {
        const val MAX_REDIRECTIONS = 10
    }

    private val cookies = LinkedHashMap<String, String>()

    fun get(
        url: String,
        headers: Map<String, String> = emptyMap(),
        followRedirects: Boolean = true,
    ): HttpResponse = execute("GET", url, null, headers, followRedirects)

    fun postForm(
        url: String,
        formulaire: Map<String, String>,
        headers: Map<String, String> = emptyMap(),
        followRedirects: Boolean = true,
    ): HttpResponse {
        val corps = encoderFormulaire(formulaire).toByteArray(StandardCharsets.UTF_8)
        val entetes = headers + ("Content-Type" to "application/x-www-form-urlencoded")
        return execute("POST", url, corps, entetes, followRedirects)
    }

    /** POST sans corps (ou avec un corps déjà encodé), utilisé par les commandes Blink. */
    fun post(
        url: String,
        headers: Map<String, String> = emptyMap(),
        body: String? = null,
    ): HttpResponse {
        val corps = body?.toByteArray(StandardCharsets.UTF_8)
        return execute("POST", url, corps, headers, true)
    }

    fun clearCookies() {
        cookies.clear()
    }

    private fun execute(
        methode: String,
        url: String,
        corps: ByteArray?,
        headers: Map<String, String>,
        followRedirects: Boolean,
    ): HttpResponse {
        var methodeCourante = methode
        var corpsCourant = corps
        var adresse = URL(url)
        var redirections = 0

        while (true) {
            val connexion = adresse.openConnection() as HttpURLConnection
            try {
                connexion.requestMethod = methodeCourante
                connexion.connectTimeout = connectTimeoutMs
                connexion.readTimeout = readTimeoutMs
                // Les redirections sont suivies à la main : HttpURLConnection
                // ne remonte pas les Set-Cookie des réponses 302 intermédiaires,
                // et Blink attache la session OAuth à ces cookies.
                connexion.instanceFollowRedirects = false
                connexion.useCaches = false
                connexion.setRequestProperty("Accept-Language", "fr-FR,fr;q=0.9,en;q=0.8")

                val cookieHeader = cookies.entries.joinToString("; ") { "${it.key}=${it.value}" }
                if (cookieHeader.isNotEmpty()) connexion.setRequestProperty("Cookie", cookieHeader)
                for ((nom, valeur) in headers) connexion.setRequestProperty(nom, valeur)

                if (corpsCourant != null) {
                    connexion.doOutput = true
                    connexion.setFixedLengthStreamingMode(corpsCourant.size)
                    connexion.outputStream.use { it.write(corpsCourant!!) }
                }

                val statut = connexion.responseCode
                capturerCookies(connexion)

                val entetesReponse = LinkedHashMap<String, String>()
                for ((nom, valeurs) in connexion.headerFields) {
                    if (nom == null || valeurs.isNullOrEmpty()) continue
                    entetesReponse[nom.lowercase()] = valeurs.joinToString(", ")
                }

                if (followRedirects && statut in 301..308) {
                    val location = connexion.getHeaderField("Location")
                    if (!location.isNullOrBlank()) {
                        val suivante = try {
                            URL(adresse, location)
                        } catch (_: java.net.MalformedURLException) {
                            // Schéma personnalisé (immedia-blink://) : le code
                            // d'autorisation est rendu tel quel à l'appelant.
                            null
                        }
                        // Une redirection vers immedia-blink:// est le code
                        // d'autorisation lui-même : elle est rendue à l'appelant.
                        if (suivante != null && (suivante.protocol == "http" || suivante.protocol == "https")) {
                            redirections += 1
                            if (redirections > MAX_REDIRECTIONS) {
                                throw java.io.IOException("Trop de redirections HTTP.")
                            }
                            if (statut == 303 || ((statut == 301 || statut == 302) && methodeCourante == "POST")) {
                                methodeCourante = "GET"
                                corpsCourant = null
                            }
                            adresse = suivante
                            continue
                        }
                    }
                }

                // Le corps des redirections est inutile : seul Location compte.
                val texte = if (statut in 300..399) {
                    ""
                } else {
                    val flux: InputStream? = if (statut >= 400) connexion.errorStream else connexion.inputStream
                    flux?.use { lireTout(it) } ?: ""
                }

                return HttpResponse(statut, entetesReponse, texte)
            } finally {
                connexion.disconnect()
            }
        }
    }

    private fun capturerCookies(connexion: HttpURLConnection) {
        val champs = connexion.headerFields ?: return
        for ((nom, valeurs) in champs) {
            if (nom == null || !nom.equals("Set-Cookie", ignoreCase = true) || valeurs == null) continue
            for (valeur in valeurs) {
                val paire = valeur.substringBefore(';').trim()
                if (!paire.contains('=')) continue
                val nomCookie = paire.substringBefore('=').trim()
                val valeurCookie = paire.substringAfter('=', "").trim()
                if (nomCookie.isNotEmpty()) cookies[nomCookie] = valeurCookie
            }
        }
    }

    private fun encoderFormulaire(formulaire: Map<String, String>): String =
        formulaire.entries.joinToString("&") { (cle, valeur) ->
            "${URLEncoder.encode(cle, "UTF-8")}=${URLEncoder.encode(valeur, "UTF-8")}"
        }

    private fun lireTout(flux: InputStream): String {
        val sortie = ByteArrayOutputStream()
        val tampon = ByteArray(8_192)
        while (true) {
            val lus = flux.read(tampon)
            if (lus < 0) break
            sortie.write(tampon, 0, lus)
        }
        return sortie.toString("UTF-8")
    }
}
