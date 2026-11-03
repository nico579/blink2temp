package com.nico.blink2temp

import com.nico.blink2temp.update.ReleaseMetadata
import com.nico.blink2temp.update.ReleaseVersions
import com.nico.blink2temp.update.UpdateException
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

class ReleaseUpdatesTest {
    private val digest = "a".repeat(64)

    private fun metadata(version: String = "0.2.0"): JSONObject {
        val tag = "v$version"
        val name = "blink2temp-$version.apk"
        return JSONObject()
            .put("tag_name", tag)
            .put("draft", false)
            .put("prerelease", false)
            .put("body", "Notes de version")
            .put(
                "assets",
                JSONArray().put(
                    JSONObject()
                        .put("name", name)
                        .put("size", 1234)
                        .put("digest", "sha256:$digest")
                        .put(
                            "browser_download_url",
                            "https://github.com/nico579/blink2temp/releases/download/$tag/$name",
                        ),
                ),
            )
    }

    private fun rejected(action: () -> Unit) {
        try {
            action()
            fail("Une mise à jour invalide doit être refusée")
        } catch (_: UpdateException) {
        }
    }

    @Test
    fun versionsCompareesNumeriquementEtSansRetourArriere() {
        assertTrue(ReleaseVersions.newer("v0.10.0", "0.9.9"))
        assertFalse(ReleaseVersions.newer("0.1.0", "v0.1.0"))
        assertNull(ReleaseMetadata.parse(metadata("0.0.9"), "0.1.0"))
        for (bad in listOf("0.2.0-beta", "0.02.0", "../0.2.0", "0.2", "2147483648.0.0")) {
            rejected { ReleaseVersions.parse(bad) }
        }
    }

    @Test
    fun metadonneesValides() {
        val release = ReleaseMetadata.parse(metadata(), "0.1.0")!!
        assertEquals("0.2.0", release.version)
        assertEquals("v0.2.0", release.tag)
        assertEquals("blink2temp-0.2.0.apk", release.name)
        assertEquals(digest, release.sha256)
        assertEquals(1234L, release.size)
        assertEquals("Notes de version", release.notes)
        assertNull(release.checksumUrl)
    }

    @Test
    fun metadonneesHostilesRefusees() {
        val mutations: List<(JSONObject) -> Unit> = listOf(
            { it.put("draft", true) },
            { it.put("prerelease", true) },
            { it.getJSONArray("assets").getJSONObject(0).put("browser_download_url", "https://example.com/app.apk") },
            { it.getJSONArray("assets").getJSONObject(0).put("size", "1234") },
            { it.getJSONArray("assets").getJSONObject(0).put("digest", "sha256:bad") },
            { it.getJSONArray("assets").getJSONObject(0).remove("digest") },
            { it.getJSONArray("assets").put(it.getJSONArray("assets").getJSONObject(0)) },
            { it.put("assets", JSONArray()) },
        )
        for (mutate in mutations) {
            val json = metadata()
            mutate(json)
            rejected { ReleaseMetadata.parse(json, "0.1.0") }
        }
    }

    @Test
    fun empreinteDeSecoursDansLeFichierDeControles() {
        val json = metadata()
        json.getJSONArray("assets").getJSONObject(0).remove("digest")
        val checksumUrl =
            "https://github.com/nico579/blink2temp/releases/download/v0.2.0/SHA256SUMS.txt"
        json.getJSONArray("assets").put(
            JSONObject().put("name", "SHA256SUMS.txt").put("browser_download_url", checksumUrl),
        )

        val release = ReleaseMetadata.parse(json, "0.1.0")!!
        assertEquals(checksumUrl, release.checksumUrl)
        assertNull(release.sha256)
    }
}
