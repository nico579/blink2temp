package com.nico.blink2temp.blink

import java.security.MessageDigest
import java.security.SecureRandom
import java.util.Base64

/** Génération PKCE (RFC 7636, méthode S256). */
object Pkce {
    /** Code verifier : 32 octets aléatoires encodés en base64url sans remplissage. */
    fun generateVerifier(random: SecureRandom = SecureRandom()): String {
        val octets = ByteArray(32)
        random.nextBytes(octets)
        return encoder(octets)
    }

    /** code_challenge = base64url(SHA-256(verifier)). */
    fun challenge(verifier: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
            .digest(verifier.toByteArray(Charsets.US_ASCII))
        return encoder(digest)
    }

    fun encoder(octets: ByteArray): String =
        Base64.getUrlEncoder().withoutPadding().encodeToString(octets)
}
