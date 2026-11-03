package com.nico.blink2temp

import com.nico.blink2temp.blink.OAuthHtml
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class OAuthHtmlTest {
    @Test
    fun extraitJetonCsrf() {
        val html = """
            <html><body>
            <script id="oauth-args" type="application/json">{"csrf-token":"jeton-123","autre":1}</script>
            </body></html>
        """.trimIndent()
        assertEquals("jeton-123", OAuthHtml.extractCsrfToken(html))
    }

    @Test
    fun attributsDansUnAutreOrdre() {
        val html = """<script type="application/json" id="oauth-args">{"csrf-token":"abc"}</script>"""
        assertEquals("abc", OAuthHtml.extractCsrfToken(html))
    }

    @Test
    fun secoursSurJsonSimple() {
        assertEquals("xyz", OAuthHtml.extractCsrfToken("""{"csrf-token": "xyz"}"""))
    }

    @Test
    fun jetonAbsent() {
        assertNull(OAuthHtml.extractCsrfToken(null))
        assertNull(OAuthHtml.extractCsrfToken(""))
        assertNull(OAuthHtml.extractCsrfToken("<html><body>rien</body></html>"))
    }

    @Test
    fun extraitCodeAutorisation() {
        assertEquals(
            "abc",
            OAuthHtml.extractAuthorizationCode(
                "immedia-blink://applinks.blink.com/signin/callback?code=abc&state=1",
            ),
        )
        assertEquals(
            "a+b/c=",
            OAuthHtml.extractAuthorizationCode(
                "immedia-blink://applinks.blink.com/signin/callback?code=a%2Bb%2Fc%3D&state=1",
            ),
        )
        assertNull(OAuthHtml.extractAuthorizationCode("immedia-blink://callback?state=1"))
        assertNull(OAuthHtml.extractAuthorizationCode(null))
    }
}
