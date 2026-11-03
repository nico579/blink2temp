package com.nico.blink2temp

import com.nico.blink2temp.blink.Pkce
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PkceTest {
    @Test
    fun vecteurOfficielRfc7636() {
        val verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        assertEquals(
            "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
            Pkce.challenge(verifier),
        )
    }

    @Test
    fun verifierAleatoireUtilisable() {
        val verifier = Pkce.generateVerifier()
        assertEquals(43, verifier.length)
        assertTrue(verifier.all { it.isLetterOrDigit() || it == '-' || it == '_' })
        assertNotEquals(verifier, Pkce.generateVerifier())
        assertEquals(43, Pkce.challenge(verifier).length)
    }
}
