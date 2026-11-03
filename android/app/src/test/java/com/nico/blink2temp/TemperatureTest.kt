package com.nico.blink2temp

import com.nico.blink2temp.core.Temperature
import com.nico.blink2temp.core.TemperatureUnit
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.util.Locale

class TemperatureTest {
    @Test
    fun conversionFahrenheitVersCelsius() {
        assertEquals(0.0, Temperature.fahrenheitToCelsius(32.0)!!, 0.0001)
        assertEquals(100.0, Temperature.fahrenheitToCelsius(212.0)!!, 0.0001)
        assertEquals(18.2, Temperature.fahrenheitToCelsius(64.7)!!, 0.0001)
        assertNull(Temperature.fahrenheitToCelsius(null))
        assertNull(Temperature.fahrenheitToCelsius(Double.NaN))
    }

    @Test
    fun unitesSelonRegion() {
        assertEquals(TemperatureUnit.FAHRENHEIT, Temperature.unitForRegion("US"))
        assertEquals(TemperatureUnit.FAHRENHEIT, Temperature.unitForRegion("us"))
        assertEquals(TemperatureUnit.FAHRENHEIT, Temperature.unitForRegion("PR"))
        assertEquals(TemperatureUnit.CELSIUS, Temperature.unitForRegion("FR"))
        assertEquals(TemperatureUnit.CELSIUS, Temperature.unitForRegion(""))
        assertEquals(TemperatureUnit.CELSIUS, Temperature.unitForRegion(null))
        assertEquals(TemperatureUnit.FAHRENHEIT, Temperature.unitFor(Locale.US))
        assertEquals(TemperatureUnit.CELSIUS, Temperature.unitFor(Locale.FRANCE))
    }

    @Test
    fun formatageEtConversionAffichage() {
        assertEquals("18.2°C", TemperatureUnit.CELSIUS.format(18.2))
        assertEquals("64.8°F", TemperatureUnit.FAHRENHEIT.format(18.2))
        assertEquals("32.0°F", TemperatureUnit.FAHRENHEIT.format(0.0))
        assertEquals("--", TemperatureUnit.CELSIUS.format(null))
        assertEquals("--", TemperatureUnit.FAHRENHEIT.format(null))
        assertEquals(64.76, TemperatureUnit.FAHRENHEIT.fromCelsius(18.2)!!, 0.0001)
    }
}
