# Blink2Temp 0.1.3

Relevé automatique en arrière-plan.

## Android

- **Relevé automatique** : WorkManager relève les caméras sélectionnées environ
  toutes les 15 minutes, même application fermée, sans réveiller les caméras.
- La tâche utilise la session et la sélection déjà enregistrées : aucun mot de
  passe n'est demandé ni stocké en arrière-plan.
- Elle attend une connexion réseau, survit au redémarrage du téléphone et
  reprend après une erreur passagère.
- L'application ouverte continue de faire un relevé immédiat ; l'historique est
  rechargé au retour au premier plan pour afficher les mesures de fond.
- Le relevé manuel « Relever » reste disponible.
- `versionCode` 4 : Android accepte l'installation par-dessus la 0.1.2.

## Ordinateur

- Aucun changement fonctionnel ; les exécutables sont reconstruits avec la
  même version.

## Vérification

- 31 tests unitaires Android, dont les règles de sélection des caméras et
  l'anti-doublon du relevé automatique.
- Tests Python et bundles reconstruits par GitHub Actions.
- APK et AAB signés avec la même clé que gpx2elev.
- Chaque fichier publié possède son empreinte SHA-256 dans `SHA256SUMS.txt`.
