package com.nico.blink2temp.data

import com.nico.blink2temp.blink.CameraInfo

/** Une mesure ponctuelle enregistrée localement. */
data class Reading(
    val timestamp: Long,
    val cameraName: String,
    val cameraId: String,
    val cameraType: String,
    val model: String,
    val outdoor: Boolean,
    val tempC: Double?,
    val battery: String,
    val batteryLevel: Int?,
    val wifi: Int?,
    val lfr: Int?,
    val status: String,
    val blinkUpdatedAt: String?,
)

/** Statistiques d'une caméra sur une fenêtre temporelle. */
data class CameraStats(
    val count: Int,
    val minC: Double,
    val avgC: Double,
    val maxC: Double,
)

fun CameraInfo.toReading(timestamp: Long): Reading = Reading(
    timestamp = timestamp,
    cameraName = name,
    cameraId = id,
    cameraType = type,
    model = model,
    outdoor = outdoor,
    tempC = tempC,
    battery = battery,
    batteryLevel = batteryLevel,
    wifi = wifi,
    lfr = lfr,
    status = status,
    blinkUpdatedAt = updatedAt,
)
