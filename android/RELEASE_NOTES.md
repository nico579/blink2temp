# Blink2Temp 0.1.7

Tableau de bord simplifié : tout l'historique s'affiche d'emblée, sans filtre de dates.

## Ordinateur

- **Suppression du filtre « Du / Au »** dans l'en-tête du graphique. Les champs
  de date et leur logique ont été retirés.
- **Tout l'historique est toujours chargé** (`/api/history?hours=all`) : la
  courbe complète apparaît dès l'ouverture.
- Le zoom molette, le déplacement transversal et la frise chronologique restent
  disponibles pour explorer ensuite.
- Le rafraîchissement automatique toutes les 60 secondes conserve seulement le
  zoom en cours.
- `↺ Réinitialiser vue` et le double-clic ramènent à la vue complète.
- Le bouton de mise à jour depuis GitHub reste disponible.

## Android

- Aucun changement fonctionnel : `versionCode` 8 pour autoriser l'installation
  par-dessus la 0.1.6.

## Vérification

- Tests Python et bundles reconstruits par GitHub Actions.
- APK et AAB signés avec la même clé que gpx2elev.
- Chaque fichier publié possède son empreinte SHA-256 dans `SHA256SUMS.txt`.
