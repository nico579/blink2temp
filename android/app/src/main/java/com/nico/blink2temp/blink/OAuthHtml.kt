package com.nico.blink2temp.blink

import org.json.JSONObject
import java.net.URLDecoder

/** Extraction des données utiles dans les pages HTML du parcours OAuth Blink. */
object OAuthHtml {
    private val scriptRegex = Regex(
        """<script[^>]*id\s*=\s*["']oauth-args["'][^>]*>(.*?)</script>""",
        setOf(RegexOption.DOT_MATCHES_ALL, RegexOption.IGNORE_CASE),
    )
    private val csrfFallbackRegex = Regex("""["']csrf-token["']\s*:\s*["']([^"']+)["']""")

    /** Lit le jeton CSRF contenu dans `<script id="oauth-args" type="application/json">`. */
    fun extractCsrfToken(html: String?): String? {
        if (html.isNullOrBlank()) return null

        for (correspondance in scriptRegex.findAll(html)) {
            val contenu = correspondance.groupValues[1].trim()
            if (!contenu.startsWith("{")) continue
            try {
                val jeton = JSONObject(contenu).optString("csrf-token").trim()
                if (jeton.isNotEmpty()) return jeton
            } catch (_: Exception) {
                // Passage au bloc suivant / à l'expression régulière de secours.
            }
        }

        return csrfFallbackRegex.find(html)?.groupValues?.get(1)?.takeIf { it.isNotBlank() }
    }

    /** Extrait le paramètre `code` de l'URL de redirection immedia-blink://. */
    fun extractAuthorizationCode(location: String?): String? {
        if (location.isNullOrBlank()) return null
        val requete = location.substringAfter('?', "")
        if (requete.isEmpty()) return null
        for (parametre in requete.split('&')) {
            val separateur = parametre.indexOf('=')
            val cle = if (separateur >= 0) parametre.substring(0, separateur) else parametre
            if (cle != "code") continue
            val valeur = if (separateur >= 0) parametre.substring(separateur + 1) else ""
            if (valeur.isEmpty()) return null
            return try {
                URLDecoder.decode(valeur, "UTF-8")
            } catch (_: Exception) {
                valeur
            }
        }
        return null
    }
}
