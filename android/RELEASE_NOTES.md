# Blink2Temp 0.1.0

Première version Android et premiers exécutables autonomes pour ordinateur.

## Android

- Connexion Blink native OAuth 2 + PKCE, vérification 2FA ; le mot de passe
  n'est jamais enregistré.
- Sélection des caméras à traiter : seules les caméras cochées sont relevées,
  enregistrées et affichées.
- Relevé passif de l'écran d'accueil Blink, sans réveiller les caméras.
- Historique local (30 jours, 5 000 mesures), statistiques min / moyenne / max
  et courbe sur 6 h, 24 h ou 7 jours.
- **Mises à jour intégrées** : l'application vérifie les releases GitHub,
  télécharge l'APK, contrôle son empreinte SHA-256, son identifiant, son
  numéro de version et sa signature avant de lancer l'installateur Android.

## Ordinateur

- Exécutables autonomes Windows x64, Linux x64, macOS Intel et macOS Apple
  Silicon : Python, blinkpy et les dépendances sont inclus.
- Tableau de bord web local, relevé horaire, historique SQLite et export CSV.
- Données conservées dans le dossier utilisateur (config.json,
  temperatures.db, journaux).

## Vérification

- Tests unitaires Android et Python exécutés par GitHub Actions.
- APK et AAB signés avec la même clé que gpx2elev.
- Chaque fichier publié possède son empreinte SHA-256 dans
  `SHA256SUMS.txt`.
