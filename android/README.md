# Blink2Temp — application Android

Application Android native de relevé des températures Blink, construite avec
Kotlin et Jetpack Compose (même pile que le projet `gpx2elev` : Gradle 8.7,
AGP 8.5.2, Kotlin 1.9.24, compileSdk 34, minSdk 26).

Version : **0.1.0** (`VERSION`), `versionCode` 1.

## Fonctionnalités

- **Connexion Blink native** : OAuth 2 « Authorization Code + PKCE », page de
  connexion HTML, vérification 2FA, échange puis rafraîchissement du jeton.
  Aucun mot de passe n'est enregistré : seul le jeton Blink est conservé.
- **Sélection des caméras à traiter** : les caméras découvertes sur l'écran
  d'accueil sont listées avec une case à cocher. Seules les caméras cochées
  sont relevées, enregistrées et affichées. La sélection est persistée et
  « Tout / Rien » permet de la modifier rapidement.
- **Relevé passif** : lecture de `GET /api/v3/accounts/{id}/homescreen`, sans
  réveiller les caméras (aucune consommation de pile supplémentaire).
- **Historique local** : fichier JSON privé (`historique.json`), purge à
  30 jours et plafond de 5 000 mesures.
- **Cartes caméra** : température, modèle, intérieur/extérieur, statut en
  ligne, pile, Wi-Fi et horodatage.
- **Statistiques et courbe** : min / moyenne / max par caméra sur 6 h, 24 h ou
  7 jours, avec une courbe multi-caméras.
- **Unité unique** : °F pour les territoires qui l'utilisent (États-Unis et
  assimilés), °C sinon, comme la page web.
- **Mises à jour intégrées** : comme gpx2elev, l'application interroge la
  dernière release GitHub, télécharge l'APK puis vérifie son empreinte
  SHA-256, son identifiant, son `versionCode` et sa signature avant de lancer
  l'installateur Android. Aucun compte Play Store n'est nécessaire.

## Compilation

Prérequis : JDK 17 ou 21, SDK Android (plateforme 34 + build-tools 34.0.0).

```powershell
cd android
.\build.ps1            # tests + APK debug
.\build.ps1 -Mode apk  # APK release (signé avec la clé debug)
.\build.ps1 -Mode tests
```

Ou directement :

```powershell
$env:JAVA_HOME = "$env:USERPROFILE\.jdks\jbr-21.0.11"
.\gradlew.bat testDebugUnitTest assembleDebug --offline
.\gradlew.bat assembleRelease bundleRelease --offline
```

Fichiers produits :

- `app/build/outputs/apk/debug/app-debug.apk`
- `app/build/outputs/apk/release/app-release.apk`
- `app/build/outputs/bundle/release/app-release.aab`

La clé de signature est `app/debug.keystore`, la même que gpx2elev (alias
`androiddebugkey`). Elle n'est jamais versionnée : GitHub Actions la restaure
depuis le secret `ANDROID_KEYSTORE_BASE64` au moment de publier.

## Tests unitaires

24 tests JVM couvrent :

- conversion °F → °C, arrondi, choix de l'unité selon le territoire ;
- PKCE (vecteur officiel RFC 7636) ;
- extraction du jeton CSRF et du code d'autorisation OAuth ;
- catalogue des modèles Blink et détection des caméras extérieures ;
- parsing de la réponse `/homescreen` (caméras, Minis, sonnettes) ;
- persistance de l'historique, purge 30 jours, plafond 5 000 entrées et
  statistiques min / moyenne / max ;
- versions des mises à jour, métadonnées de release et refus des URL, tailles,
  empreintes ou fichiers incohérents.

```powershell
.\gradlew.bat testDebugUnitTest --offline
```

## Architecture

```text
app/src/main/java/com/nico/blink2temp/
├── MainActivity.kt          # Point d'entrée Compose
├── AppViewModel.kt          # État UI, connexion, relevés, sélection, historique
├── blink/
│   ├── BlinkClient.kt       # OAuth v2 + PKCE, 2FA, refresh, homescreen
│   ├── HttpTransport.kt     # HttpURLConnection + bocal de cookies
│   ├── Models.kt            # Session, caméra, parsing /homescreen
│   ├── OAuthHtml.kt         # CSRF et code d'autorisation
│   └── Pkce.kt              # RFC 7636 (S256)
├── core/
│   ├── CameraCatalog.kt     # Modèles Blink, détection extérieur
│   └── Temperature.kt       # Conversion et unité d'affichage
├── data/
│   ├── MeasurementStore.kt  # historique JSON (30 j / 5000)
│   ├── Reading.kt           # mesure locale + statistiques
│   └── SessionStore.kt      # SharedPreferences (jetons, sélection)
├── update/
│   ├── ReleaseUpdates.kt    # GitHub, SHA-256, identité et signature de l'APK
│   ├── UpdateFileProvider.kt
│   └── UpdateViewModel.kt   # vérification, téléchargement, installation
└── ui/
    ├── BlinkScreen.kt       # Écran Compose (thème sombre)
    └── UpdateDialog.kt      # Dialogue de mise à jour
```

## GitHub Actions

Les workflows sont à la racine du dépôt :

- `.github/workflows/ci.yml` : version commune, tests JVM + lint + APK/AAB,
  tests Python et construction des quatre bundles à chaque push et pull
  request.
- `.github/workflows/release.yml` : sur un tag `vX.Y.Z`, construit l'APK et
  l'AAB signés, les bundles Windows/Linux/macOS, vérifie signatures, tests et
  empreintes, puis publie la release GitHub.

Créer une version :

```powershell
# Mettre VERSION et versionCode à jour, puis :
git tag v0.1.0
git push origin main --tags
```

## Limites connues

- **Le parcours d'authentification n'a pas encore été validé avec un vrai
  compte Blink** (aucun identifiant n'a été utilisé pendant le développement).
  En cas d'échec, les messages d'erreur indiquent l'étape concernée.
- **Pas de synchronisation avec l'application PC** : l'historique est privé à
  l'application Android. Un export CSV pourra être ajouté ultérieurement.
- Le relevé ne réveille pas les caméras : il lit uniquement la dernière
  télémétrie disponible sur l'écran d'accueil Blink. Une caméra qui n'a pas
  communiqué récemment peut donc afficher une valeur ancienne.
- Les caméras sans capteur de température (certaines Minis, modules Sync)
  apparaissent avec `--` mais peuvent rester sélectionnées.
