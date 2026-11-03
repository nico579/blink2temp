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
        val connexion = URL(url).openConnection() as HttpURLConnection
        try {
            connexion.requestMethod = methode
            connexion.connectTimeout = connectTimeoutMs
            connexion.readTimeout = readTimeoutMs
            connexion.instanceFollowRedirects = followRedirects
            connexion.setRequestProperty("Accept-Language", "fr-FR,fr;q=0.9,en;q=0.8")

            val cookieHeader = cookies.entries.joinToString("; ") { "${it.key}=${it.value}" }
            if (cookieHeader.isNotEmpty()) connexion.setRequestProperty("Cookie", cookieHeader)
            for ((nom, valeur) in headers) connexion.setRequestProperty(nom, valeur)

            if (corps != null) {
                connexion.doOutput = true
                connexion.setFixedLengthStreamingMode(corps.size)
                connexion.outputStream.use { it.write(corps) }
            }

            val statut = connexion.responseCode
            capturerCookies(connexion)

            val entetesReponse = LinkedHashMap<String, String>()
            for ((nom, valeurs) in connexion.headerFields) {
                if (nom == null || valeurs.isNullOrEmpty()) continue
                entetesReponse[nom.lowercase()] = valeurs.joinToString(", ")
            }

            // Le corps des redirections est inutile : seul l'en-tête Location compte.
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
