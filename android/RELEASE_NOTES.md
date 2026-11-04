# Blink2Temp 0.1.1

Version corrective pour la connexion à Blink et la saisie du mot de passe.

## Android

- **Connexion Blink corrigée** : les redirections OAuth sont désormais suivies
  manuellement afin de conserver les cookies `blink-session`,
  `blink-public-session` et `csrf-protection` émis par les réponses 302
  intermédiaires. Sans ces cookies, Blink répondait
  `401 session_expired` même avec des identifiants corrects.
- Un POST redirigé en 301, 302 ou 303 est rejoué en GET, et le nombre de
  redirections est limité.
- Le message d'erreur distingue une session expirée d'identifiants incorrects.
- **Mot de passe affichable** : un bouton « Afficher » / « Masquer » permet de
  vérifier la saisie avant de se connecter.
- `versionCode` 2 : Android accepte l'installation par-dessus la version 0.1.0
  et la mise à jour intégrée peut s'appliquer.

## Ordinateur

- Aucun changement fonctionnel ; les exécutables sont reconstruits avec la
  même version.

## Vérification

- 26 tests unitaires Android, dont deux tests de transport HTTP couvrant la
  conservation des cookies et la redirection POST → GET.
- Tests Python et bundles reconstruits par GitHub Actions.
- APK et AAB signés avec la même clé que gpx2elev.
- Chaque fichier publié possède son empreinte SHA-256 dans `SHA256SUMS.txt`.
