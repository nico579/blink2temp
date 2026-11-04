package com.nico.blink2temp

import com.nico.blink2temp.blink.HttpTransport
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.io.IOException
import java.net.InetSocketAddress
import java.net.ServerSocket
import java.util.Collections
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit

/** Serveur HTTP minimal : vérifie les cookies et les redirections sans Android. */
class HttpTransportTest {
    private lateinit var serveur: ServerSocket
    private lateinit var thread: Thread
    private val reponses = LinkedBlockingQueue<String>()
    private val requetes = Collections.synchronizedList(mutableListOf<String>())

    @Before
    fun demarrer() {
        serveur = ServerSocket().apply { bind(InetSocketAddress("127.0.0.1", 0)) }
        thread = Thread {
            while (!serveur.isClosed) {
                try {
                    serveur.accept().use { socket ->
                        socket.soTimeout = 5_000
                        val entree = socket.getInputStream().bufferedReader(Charsets.ISO_8859_1)
                        val lignes = mutableListOf<String>()
                        while (true) {
                            val ligne = entree.readLine() ?: break
                            lignes.add(ligne)
                            if (ligne.isEmpty()) break
                        }
                        val longueur = lignes.firstOrNull { it.startsWith("Content-Length:", true) }
                            ?.substringAfter(':')?.trim()?.toIntOrNull() ?: 0
                        if (longueur > 0) {
                            val corps = CharArray(longueur)
                            var lus = 0
                            while (lus < longueur) {
                                val compte = entree.read(corps, lus, longueur - lus)
                                if (compte < 0) break
                                lus += compte
                            }
                        }
                        requetes.add(lignes.joinToString("\n"))
                        val reponse = reponses.poll(5, TimeUnit.SECONDS) ?: return@use
                        socket.getOutputStream().apply {
                            write(reponse.toByteArray(Charsets.ISO_8859_1))
                            flush()
                        }
                    }
                } catch (erreur: IOException) {
                    if (!serveur.isClosed) throw erreur
                }
            }
        }.apply { isDaemon = true; start() }
    }

    @After
    fun arreter() {
        serveur.close()
        thread.join(3_000)
    }

    private fun url(chemin: String) = "http://127.0.0.1:${serveur.localPort}$chemin"

    private fun reponse(
        code: Int,
        corps: String = "",
        entetes: List<String> = emptyList(),
    ): String = buildString {
        append("HTTP/1.1 $code Reponse\r\n")
        append("Content-Length: ${corps.toByteArray(Charsets.ISO_8859_1).size}\r\n")
        for (entete in entetes) append("$entete\r\n")
        append("Connection: close\r\n\r\n")
        append(corps)
    }

    @Test
    fun conserveLesCookiesDesRedirectionsIntermediaires() {
        reponses.add(
            reponse(
                302,
                entetes = listOf(
                    "Set-Cookie: blink-session=abc123; Path=/; HttpOnly",
                    "Location: /suite",
                ),
            ),
        )
        reponses.add(reponse(200, "ok"))

        val resultat = HttpTransport().get(url("/depart"))

        assertEquals(200, resultat.status)
        assertEquals("ok", resultat.body)
        assertEquals(2, requetes.size)
        assertTrue(
            "Le cookie de la redirection doit accompagner la requête suivante : ${requetes[1]}",
            requetes[1].contains("Cookie: blink-session=abc123"),
        )
    }

    @Test
    fun postRedirige303EnGetEtConserveLaSession() {
        reponses.add(
            reponse(
                303,
                entetes = listOf(
                    "Set-Cookie: csrf-protection=jeton; Path=/oauth/v2",
                    "Location: /autorisation",
                ),
            ),
        )
        reponses.add(
            reponse(
                302,
                entetes = listOf(
                    "Location: immedia-blink://applinks.blink.com/signin/callback?code=abc",
                ),
            ),
        )

        val resultat = HttpTransport().postForm(url("/connexion"), mapOf("a" to "b"))

        assertEquals(302, resultat.status)
        assertEquals(
            "immedia-blink://applinks.blink.com/signin/callback?code=abc",
            resultat.header("location"),
        )
        assertEquals(2, requetes.size)
        assertTrue(requetes[1].startsWith("GET "))
        assertTrue(requetes[1].contains("Cookie: csrf-protection=jeton"))
    }
}
