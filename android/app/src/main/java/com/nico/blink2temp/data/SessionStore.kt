package com.nico.blink2temp.data

import android.content.Context
import com.nico.blink2temp.blink.BlinkSession

/**
 * Persistance de la session Blink (jetons OAuth), de l'email mémorisé et de la
 * sélection de caméras. Le mot de passe n'est jamais enregistré.
 */
class SessionStore(context: Context) {
    private val prefs = context.getSharedPreferences("blink2temp", Context.MODE_PRIVATE)

    fun loadSession(): BlinkSession? {
        val access = prefs.getString(KEY_ACCESS, null) ?: return null
        val refresh = prefs.getString(KEY_REFRESH, null) ?: return null
        val host = prefs.getString(KEY_HOST, null) ?: return null
        val account = prefs.getString(KEY_ACCOUNT, null) ?: return null
        val hardware = prefs.getString(KEY_HARDWARE, null) ?: return null
        return BlinkSession(
            username = prefs.getString(KEY_USERNAME, "") ?: "",
            hardwareId = hardware,
            accessToken = access,
            refreshToken = refresh,
            expiresAt = prefs.getLong(KEY_EXPIRES, 0L),
            host = host,
            accountId = account,
        )
    }

    fun saveSession(session: BlinkSession) {
        prefs.edit()
            .putString(KEY_USERNAME, session.username)
            .putString(KEY_HARDWARE, session.hardwareId)
            .putString(KEY_ACCESS, session.accessToken)
            .putString(KEY_REFRESH, session.refreshToken)
            .putLong(KEY_EXPIRES, session.expiresAt)
            .putString(KEY_HOST, session.host)
            .putString(KEY_ACCOUNT, session.accountId)
            .apply()
    }

    fun clearSession() {
        prefs.edit()
            .remove(KEY_ACCESS)
            .remove(KEY_REFRESH)
            .remove(KEY_EXPIRES)
            .remove(KEY_HOST)
            .remove(KEY_ACCOUNT)
            .apply()
    }

    fun loadHardwareId(): String? = prefs.getString(KEY_HARDWARE, null)

    fun saveHardwareId(value: String) {
        prefs.edit().putString(KEY_HARDWARE, value).apply()
    }

    fun loadEmail(): String = prefs.getString(KEY_EMAIL, "") ?: ""

    fun saveEmail(value: String) {
        prefs.edit().putString(KEY_EMAIL, value).apply()
    }

    /** null = aucune sélection enregistrée (premier lancement). */
    fun loadSelection(): Set<String>? = prefs.getStringSet(KEY_SELECTION, null)?.toSet()

    fun saveSelection(names: Set<String>) {
        prefs.edit().putStringSet(KEY_SELECTION, names).apply()
    }

    /** Option « réveiller les caméras avant lecture », désactivée par défaut. */
    fun loadWakeCameras(): Boolean = prefs.getBoolean(KEY_WAKE, false)

    fun saveWakeCameras(enabled: Boolean) {
        prefs.edit().putBoolean(KEY_WAKE, enabled).apply()
    }

    /** Dernier réveil effectué, pour espacer les réveils automatiques. */
    fun loadLastWake(): Long? = prefs.getLong(KEY_LAST_WAKE, 0L).takeIf { it > 0L }

    fun saveLastWake(timestamp: Long) {
        prefs.edit().putLong(KEY_LAST_WAKE, timestamp).apply()
    }

    private companion object {
        const val KEY_USERNAME = "username"
        const val KEY_HARDWARE = "hardware_id"
        const val KEY_ACCESS = "access_token"
        const val KEY_REFRESH = "refresh_token"
        const val KEY_EXPIRES = "expires_at"
        const val KEY_HOST = "host"
        const val KEY_ACCOUNT = "account_id"
        const val KEY_EMAIL = "email"
        const val KEY_SELECTION = "selection"
        const val KEY_WAKE = "wake_cameras"
        const val KEY_LAST_WAKE = "last_wake"
    }
}
