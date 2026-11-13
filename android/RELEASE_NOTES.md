# Blink2Temp 0.1.8

Les en-têtes du tableau de synthèse affichent enfin leur unité, et le README montre l'application.

## Ordinateur

- **En-têtes du tableau de synthèse corrigés** : ils affichaient
  « Min (${UNITE_TEMP}) », un gabarit jamais interprété, au lieu de
  « Min (°C) » ou « Min (°F) » selon le pays du navigateur.
- **Captures d'écran dans le README** : le tableau de bord web et
  l'application Android.
- **Le bundle macOS Apple Silicon revient** : il se construit désormais sur
  `macos-latest`, l'image `macos-14` n'étant plus servie par GitHub depuis le
  10 novembre.

## Android

- Aucun changement fonctionnel : `versionCode` 9 pour autoriser l'installation
  par-dessus la 0.1.7.

## Vérification

- Tests Python et bundles reconstruits par GitHub Actions.
- APK et AAB signés avec la même clé que gpx2elev.
- Chaque fichier publié possède son empreinte SHA-256 dans `SHA256SUMS.txt`.
