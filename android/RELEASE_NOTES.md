# Blink2Temp 0.1.5

Réveil des caméras uniquement lorsque leur température n'a pas évolué, sur Android comme sur ordinateur.

## Android

- **Nouvelle option « Réveiller les caméras si la température n'a pas changé »**,
  désactivée par défaut.
- Une commande photo est envoyée **uniquement** aux caméras sélectionnées dont la
  température passive est identique à la dernière mesure (tolérance 0,05 °C).
  Une caméra dont la température a bougé, ou qui n'en remonte pas, n'est jamais
  réveillée.
- Après le réveil, l'écran d'accueil Blink est relu pour afficher la température
  fraîche.
- **Économie de pile** : en arrière-plan, au plus un réveil par heure. Le bouton
  « Relever maintenant » force le réveil sans attendre ce délai, mais toujours
  uniquement pour les températures inchangées.
- Un avertissement rappelle qu'une photo consomme la pile et peut durer jusqu'à
  une minute par caméra.
- `versionCode` 6 : Android accepte l'installation par-dessus la 0.1.4.

## Ordinateur

- **Même option dans le tableau de bord web** : case à cocher dans l'en-tête,
  enregistrée dans `config.json` (`reveiller_cameras`).
- Le relevé planifié applique le même délai d'une heure ; le bouton
  « Relever maintenant » force le réveil.
- Nouvelles options CLI : `--reveiller` et `--force-reveil`.
- Les caméras qui ne remontent pas de température ne sont plus affichées dans
  les cartes, comme sur Android.

## Vérification

- Tests unitaires Android complétés (règle de température inchangée et délai
  entre réveils), tests Python complétés avec un scénario de réveil sélectif.
- Tests Python et bundles reconstruits par GitHub Actions.
- APK et AAB signés avec la même clé que gpx2elev.
- Chaque fichier publié possède son empreinte SHA-256 dans `SHA256SUMS.txt`.
