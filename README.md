# 🌡️ Blink2Temp

Application de surveillance et de relevé automatique des températures des **caméras extérieures Blink (Blink Outdoor, XT, XT2)**, toutes les heures.

Développée en s'appuyant sur l'architecture et les principes de robustesse du projet `blink` / `blink2video`.

---

## 🚀 Fonctionnalités principales

1. **Relève horaire automatisée** :
   - Interroge l'API Blink toutes les heures (alignée sur les heures rondes : 10:00, 11:00, 12:00...).
   - **Préservation des piles** : effectue une lecture passive de l'écran d'accueil cloud (`homescreen`), sans réveiller physiquement la caméra (aucun déclenchement intempestif de photo ni consommation superflue de batterie lithium).
   - **Réveil ciblé optionnel** : si la température passive n'a pas évolué depuis la dernière mesure, une commande photo peut forcer la caméra à renvoyer une valeur fraîche. Désactivé par défaut, au plus une fois par heure en relève planifiée, et jamais pour une caméra sans température ou dont la valeur a changé.

2. **Ciblage spécifique des caméras extérieures (Outdoor)** :
   - Filtre automatiquement les modèles extérieurs (`catalina` pour Blink Outdoor Gen 3, `sedona` pour Blink Outdoor 4, `canary`/`xt2`/`xt`).
   - Exclut les caméras intérieures (ex: Blink Mini / `owl` qui n'ont pas de capteur de température extérieure).
   - Convertit automatiquement les valeurs brutes Fahrenheit en Celsius avec précision à 0.1 °C.

3. **Historique & Base de données SQLite** :
   - Stockage persistant dans `temperatures.db`.
   - Conservation de la température (°C et °F), du niveau de pile (`ok`, `low`), de la qualité Wi-Fi, du statut réseau et de l'horodatage précis.
   - Statistiques complètes : minimum, maximum, moyenne, nombre de mesures.

4. **Tableau de bord Web interactif (http://localhost:8770)** :
   - **Courbes des températures interactives avec zoom molette & déplacement transversal** :
     - 🖱️ **Molette souris** : Zoome et dézoome dynamiquement sur n'importe quelle date/heure sous le curseur.
     - ↔️ **Déplacement transversal sur l'axe des dates** :
       - **Glisser sur l'axe des dates ou la courbe** : Cliquez et déplacez transversalement pour faire défiler le temps (curseur `ew-resize`).
       - **Shift + Molette** (ou molette horizontale) : Fait défiler directement l'axe des dates de gauche à droite.
       - **Frise chronologique inférieure (minimap)** : Cliquez ou glissez directement sur le bandeau temporel en bas du graphique pour naviguer instantanément à n'importe quelle date.
       - **Boutons de navigation transversale** : Boutons `◀ Reculer` et `Avancer ▶` pour décaler le temps d'un quart de vue par clic.
     - 🎯 **Double-clic ou bouton** : Réinitialise instantanément la vue à tout l'historique.
     - 📌 **Survol & HUD Tooltip** : Ligne guide verticale et infobulle affichant l'horodatage exact et la température de chaque caméra.
     - 👁️ **Légende filtrable** : Cliquez sur le nom d'une caméra pour masquer ou afficher sa courbe.
     - ⚡ **100% autonome** : Rendu Canvas fluide 60fps sans aucune dépendance externe ou CDN (fonctionne hors-ligne).
   - Cartes visuelles de télémétrie en temps réel par caméra (température, pile, Wi-Fi, statut).
   - Synthèse statistique calculée sur la période affichée (min, max, moyenne).
   - Bouton d'actualisation immédiate (*Relever maintenant*) et d'export CSV pour Excel.
   - Case **« Réveiller les caméras si la température n'a pas changé »** (pile, avertissement affiché), identique à l'application Android. Les caméras sans température ne sont pas affichées.

5. **Intégration Windows transparente** :
   - Réutilise automatiquement la session authentifiée existante de `blink2video` (`%LOCALAPPDATA%\blink2video\blink_auth.json`). Aucun mot de passe à retaper !
   - Prise en charge d'une tâche planifiée Windows en arrière-plan (`schtasks`) via `--install-task`.
   - Lanceur interactif double-cliquable : `lancer_blink2temp.bat`.

6. **Mise à jour depuis GitHub** :
   - Bouton **« Mettre à jour »** dans le tableau de bord, aligné sur la dernière release publiée du dépôt.
   - Vérification silencieuse et mise en cache (six heures), sans bloquer l'interface ni le relevé.
   - Archive de la plateforme téléchargée, empreinte SHA-256 vérifiée, nouvel exécutable testé (`--version`) avant tout remplacement, puis redémarrage automatique avec les mêmes arguments.
   - Depuis les sources (dépôt git), l'équivalent est un `git pull --ff-only` : rien n'est modifié si le tirage échoue.

---

## 📦 Structure des fichiers

```text
C:\Users\Nico\Documents\blink2temp\
├── blink2temp.py          # Point d'entrée principal (CLI & boucle horaire)
├── collector.py           # Logique d'interrogation Blink et filtrage outdoor
├── storage.py             # Gestionnaire de base de données SQLite (temperatures.db)
├── scheduler.py           # Boucle d'attente horaire et gestion des signaux d'arrêt
├── web.py                 # Serveur HTTP local et tableau de bord interactif
├── updater.py             # Mise à jour depuis la dernière release GitHub
├── VERSION                # Version de l'application (alignée sur android/VERSION)
├── blink_auth.py          # Authentification Blink, 2FA et reprise de session
├── blink_tls.py           # Contexte TLS strict avec certifi
├── autostart.py           # Gestion de la tâche planifiée Windows
├── lancer_blink2temp.bat  # Lanceur batch avec menu interactif
├── test_blink2temp.py     # Suite complète de tests unitaires
├── paths.py               # Dossier de données (source ou bundle autonome)
├── requirements.txt       # Dépendances Python du relevé
├── android/               # Application Android (Kotlin + Jetpack Compose)
├── tools/                 # Construction des bundles et vérifications
├── .github/workflows/     # CI et publication GitHub
└── README.md              # Documentation
```

---

## 📱 Application Android

Une application Android native (Kotlin + Jetpack Compose) est disponible dans
`android/` : connexion Blink OAuth 2 + 2FA, sélection des caméras à traiter,
relevé passif de l'écran d'accueil, historique local, statistiques et
**mises à jour intégrées** depuis les releases GitHub.

```powershell
cd android
.\build.ps1            # tests + APK debug
```

APK : `android/app/build/outputs/apk/debug/app-debug.apk` (ou
`release/app-release.apk`). Voir [`android/README.md`](android/README.md) pour
le détail, l'architecture et les limites connues.

## 🖥️ Exécutables autonomes (bundles)

Les workflows GitHub construisent aussi des exécutables autonomes avec
PyInstaller, sans Python à installer :

- Windows x64 : `blink2temp-<version>-windows-x64.zip`
- Linux x64 : `blink2temp-<version>-linux-x64.tar.gz`
- macOS Intel : `blink2temp-<version>-macos-x64.tar.gz`
- macOS Apple Silicon : `blink2temp-<version>-macos-arm64.tar.gz`

Chaque archive contient l'exécutable et un `LISEZ-MOI.txt`. Les données
(`config.json`, `temperatures.db`, journaux) sont écrites dans le dossier de
données de l'utilisateur (`%APPDATA%\Blink2Temp`, `~/.local/share/Blink2Temp`
ou `~/Library/Application Support/Blink2Temp`).

```powershell
py -m pip install -r requirements.txt -r requirements-build.txt
python tools\build_bundle.py
python tools\package_bundle.py --artifact windows-x64
```

## 🚀 CI et releases GitHub

- `.github/workflows/ci.yml` : tests Android (JVM + lint), tests Python,
  construction de l'APK, de l'AAB et des quatre bundles à chaque push.
- `.github/workflows/release.yml` : sur un tag `vX.Y.Z`, signe l'APK et l'AAB
  avec la clé de gpx2elev, construit les bundles, vérifie signatures, tests et
  empreintes SHA-256, puis publie la release GitHub.

## ⬆️ Mise à jour intégrée

Le tableau de bord affiche la version en cours et un bouton **« Vérifier la
mise à jour »** :

1. La vérification interroge `releases/latest` au plus une fois toutes les six
   heures (réponse mise en cache, donc l'interface ne dépend jamais du réseau).
2. Si une version plus récente existe, le bouton devient vert et affiche son
   numéro. Un clic confirme, télécharge l'archive de la plateforme et vérifie
   son empreinte SHA-256.
3. Le nouvel exécutable est démarré une première fois en `--version` pour
   s'assurer qu'il fonctionne, puis un petit processus de finalisation attend
   l'arrêt de l'ancienne version, remplace le binaire et relance Blink2Temp
   avec les mêmes arguments. Les données (`temperatures.db`, `config.json`,
   session Blink) ne sont jamais touchées.

Depuis une installation en sources (dépôt git), le bouton exécute
`git pull --ff-only` puis relance l'application. En cas de modifications
locales, git refuse : rien n'est modifié. Les versions publiées avant
l'ajout du fichier `VERSION` ne peuvent pas être mises à jour automatiquement
vers elles-mêmes ; la mise à jour fonctionne à partir de la version suivante.

En ligne de commande :

```powershell
python blink2temp.py --version
```

---

## ⚡ Utilisation rapide

### 1. Avec le menu interactif (recommandé sous Windows)
Double-cliquez simplement sur **`lancer_blink2temp.bat`**. Un menu vous propose :
- De lancer la surveillance horaire avec le tableau de bord Web.
- De faire un relevé immédiat.
- D'installer la tâche en arrière-plan 24/7.

### 2. En ligne de commande

#### Effectuer un relevé immédiat unique
```powershell
# Toutes les caméras extérieures
python blink2temp.py --once

# Uniquement une caméra spécifique (ex: jardin)
python blink2temp.py --once --camera jardin
```
*Sortie :*
```text
================================================================
  Blink2Temp - Releve Horaire des Cameras Outdoor Blink
=================================================================
[09:50:56] Relève des caméras extérieures en cours...
Connexion via la session enregistrée (blink_auth.json)...

Camera          Modele               Temperature      Statut       Batterie  
---------------------------------------------------------------------------
Bureau          Blink Outdoor        22.8 °C (73°F)   Hors ligne   low       
Portail         Blink Outdoor        20.6 °C (69°F)   En ligne     low       
jardin          Blink Outdoor        12.8 °C (55°F)   En ligne     ok        
---------------------------------------------------------------------------
[✓] Relevé terminé : 3 caméras outdoor enregistrées.
```

#### Lancer la surveillance horaire en continu
```powershell
python blink2temp.py --loop 60
```

#### Lancer avec le tableau de bord Web (http://localhost:8770)
```powershell
python blink2temp.py --loop 60 --web
```
Ouvrez votre navigateur sur **http://localhost:8770** pour suivre l'évolution des températures.

#### Consulter les statistiques des dernières 24h
```powershell
python blink2temp.py --stats
```

#### Consulter l'historique des relevés récents
```powershell
python blink2temp.py --history 24
```

#### Exporter l'historique en CSV (compatible Excel UTF-8)
```powershell
python blink2temp.py --export releves.csv
```

---

## 🕒 Exécution automatique en tâche de fond (Windows)

Pour que la relève s'exécute automatiquement toutes les heures en arrière-plan sans laisser de terminal ouvert :

```powershell
# Installer la tâche horaire Windows
python blink2temp.py --install-task

# Vérifier son statut
python blink2temp.py --task-status

# Pour la désinstaller à tout moment
python blink2temp.py --uninstall-task
```

La tâche utilise `pythonw.exe` de sorte qu'aucune fenêtre ne clignote sur votre écran. Chaque passage consigne son résultat dans `blink2temp.log`.

---

## 🧪 Tests unitaires

Pour exécuter la suite de tests automatisée :
```powershell
python test_blink2temp.py
```
Les tests valident :
- La conversion Fahrenheit -> Celsius.
- La détection et le filtrage des caméras extérieures.
- La persistance, les requêtes et les statistiques SQLite.
- L'exportation CSV.
- Le calcul d'alignement horaire du planificateur.
- Le bon fonctionnement des endpoints du serveur web HTTP.
