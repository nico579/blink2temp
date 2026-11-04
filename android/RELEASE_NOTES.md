# Blink2Temp 0.1.2

Version corrective pour le relevé des températures.

## Android

- **Relevé corrigé** : Blink renvoie le tier `prod` dans `tier_info`, mais l'API
  est servie par `rest-prod.immedia-semi.com`. L'application construisait
  `prod.immedia-semi.com`, nom d'hôte inexistant : l'échec DNS était affiché à
  tort comme « Pas de connexion Internet, vérifiez votre réseau ».
- Le préfixe `rest-` est maintenant ajouté automatiquement.
- Les sessions enregistrées par les versions 0.1.0 et 0.1.1 (avec l'ancien
  hôte) sont corrigées au moment du relevé : inutile de se reconnecter.
- Message réseau plus précis si Blink est réellement injoignable.
- `versionCode` 3 : Android accepte l'installation par-dessus la 0.1.1.

## Ordinateur

- Aucun changement fonctionnel ; les exécutables sont reconstruits avec la
  même version.

## Vérification

- 28 tests unitaires Android, dont la construction de l'hôte API et la
  correction des sessions existantes.
- Tests Python et bundles reconstruits par GitHub Actions.
- APK et AAB signés avec la même clé que gpx2elev.
- Chaque fichier publié possède son empreinte SHA-256 dans `SHA256SUMS.txt`.
