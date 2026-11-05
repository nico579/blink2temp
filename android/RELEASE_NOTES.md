# Blink2Temp 0.1.6

Mise à jour depuis GitHub directement dans le tableau de bord, et courbe complète dès l'ouverture.

## Ordinateur

- **Bouton « Vérifier la mise à jour »** dans l'en-tête du tableau de bord.
  - Il interroge la dernière release GitHub au plus une fois toutes les six
    heures, avec un cache local : l'interface ne dépend jamais du réseau.
  - Dès qu'une version plus récente existe, le bouton devient vert et affiche
    son numéro.
  - Un clic télécharge l'archive de la plateforme, vérifie son empreinte
    SHA-256, puis démarre le nouvel exécutable une première fois en
    `--version` : rien n'est remplacé s'il ne répond pas.
  - Un petit processus de finalisation attend ensuite l'arrêt de l'ancienne
    version, remplace le binaire de façon atomique et relance Blink2Temp avec
    les mêmes arguments. Les données (`temperatures.db`, `config.json`,
    session Blink) ne sont jamais touchées.
  - Depuis une installation en sources (dépôt git), le bouton exécute
    `git pull --ff-only` puis relance l'application. Si des modifications
    locales sont présentes, git refuse et rien n'est modifié.
- **Courbe complète à l'ouverture** : les anciens boutons de période
  (`24 h`, `3 jours`, `7 jours`, `30 jours`, `Tout`) ont été retirés. Tout
  l'historique est chargé et affiché d'emblée ; le zoom molette et le
  déplacement à la souris restent disponibles pour explorer ensuite.
  `↺ Réinitialiser vue` et le double-clic reviennent à la vue complète.
- Le rafraîchissement automatique toutes les 60 secondes conserve le zoom et
  le filtre de dates en cours.
- Nouvelle commande : `blink2temp --version`.
- Le fichier `VERSION` à la racine fait foi et reste identique à
  `android/VERSION`, vérifié par la CI.

## Android

- Aucun changement fonctionnel : `versionCode` 7 pour autoriser l'installation
  par-dessus la 0.1.5.

## Vérification

- Tests Python complétés (comparaison de versions, choix et validation des
  archives, extraction protégée contre les chemins dangereux).
- Tests Python et bundles reconstruits par GitHub Actions.
- APK et AAB signés avec la même clé que gpx2elev.
- Chaque fichier publié possède son empreinte SHA-256 dans `SHA256SUMS.txt`.
