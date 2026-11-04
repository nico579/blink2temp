# Blink2Temp 0.1.4

Caméras sans température masquées et courbe lisible avec zoom.

## Android

- **Seules les caméras qui remontent une température sont affichées.** Les
  caméras sans sonde (par exemple une Blink Mini sans température) n'apparaissent
  plus dans la liste, ne sont plus relevées ni enregistrées.
- **Courbe reprise de l'application PC** : graduations horizontales avec les
  valeurs de température, graduations verticales avec la date et l'heure,
  grille discrète et pas adapté à l'amplitude.
- **Zoom et déplacement** : pincer pour zoomer, glisser pour se déplacer,
  double-tap ou bouton « Réinitialiser » pour revenir à la vue complète. Le
  zoom reste actif lors des relevés suivants et se limite à la période choisie
  (6 h, 24 h ou 7 jours).
- Le relevé automatique en arrière-plan de la 0.1.3 est conservé.
- `versionCode` 5 : Android accepte l'installation par-dessus la 0.1.3.

## Ordinateur

- Aucun changement fonctionnel ; les exécutables sont reconstruits avec la
  même version.

## Vérification

- 31 tests unitaires Android, dont le filtrage des caméras sans température,
  les règles de sélection et l'anti-doublon du relevé automatique.
- Tests Python et bundles reconstruits par GitHub Actions.
- APK et AAB signés avec la même clé que gpx2elev.
- Chaque fichier publié possède son empreinte SHA-256 dans `SHA256SUMS.txt`.
