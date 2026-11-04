plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.nico.blink2temp"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.nico.blink2temp"
        minSdk = 26
        targetSdk = 34
        versionCode = 4
        versionName = rootProject.file("VERSION").readText().trim()
    }

    // Même clé de signature que gpx2elev. Le fichier est fourni par le secret
    // GitHub Actions au moment de la publication, ou localement pour un test.
    signingConfigs.getByName("debug") {
        val personalKey = file("debug.keystore")
        if (personalKey.exists()) {
            storeFile = personalKey
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            isShrinkResources = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }

    buildFeatures { compose = true }
    composeOptions { kotlinCompilerExtensionVersion = "1.5.14" }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.work:work-runtime-ktx:2.9.1")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    implementation("androidx.compose.ui:ui:1.6.8")
    implementation("androidx.compose.ui:ui-graphics:1.6.8")
    implementation("androidx.compose.ui:ui-tooling-preview:1.6.8")
    implementation("androidx.compose.material3:material3:1.2.1")
    implementation("androidx.compose.material:material-icons-core:1.6.8")

    testImplementation("junit:junit:4.13.2")
    // Implémentation réelle de org.json pour les tests JVM (le stub Android lève « Stub! »).
    testImplementation("org.json:json:20240303")
}
