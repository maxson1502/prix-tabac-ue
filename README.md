# prix-tabac-ue

Page de visualisation des prix du tabac duty paid dans les 27 pays de l'UE : relevés de la Commission européenne, estimation mensuelle en euros et indices Eurostat.

Adresse à partager (une fois GitHub Pages activé) : https://maxson1502.github.io/prix-tabac-ue/

## Fonctionnement

- `index.html` : la page. À chaque ouverture ou rafraîchissement, elle charge `data/ec.json` et `data/hicp.json`. Si le site est injoignable, par exemple quand le fichier est ouvert hors ligne, elle utilise la copie des données intégrée au fichier et le signale.
- `data/ec.json` : relevés du prix moyen pondéré des cigarettes publiés par la Commission (DG TAXUD), en € par paquet de 20. Chaque nouveau relevé s'ajoute à la suite des précédents.
- `data/hicp.json` : indices mensuels Eurostat (`prc_hicp_minr`) : cigarettes, tabac et ensemble, base 2025 = 100.
- `scripts/update_data.py` : récupère les deux sources et contrôle leur contenu : 27 pays, mois complets, valeurs plausibles. Il met ensuite à jour les fichiers `data/` et la copie intégrée à `index.html`. Il n'écrit rien si les contrôles échouent.
- `.github/workflows/update-data.yml` : lance ce script tous les jours à 5 h 17 UTC et enregistre les changements éventuels. En cas d'échec, GitHub envoie un e-mail au propriétaire du dépôt, et la page continue d'afficher les dernières données valides.

Pour forcer une mise à jour : onglet **Actions** → « Mise à jour des données » → **Run workflow**.

## Réglages à faire une fois

1. Rendre le dépôt public : Settings → General → *Change repository visibility*. Avec un compte gratuit, GitHub Pages l'exige.
2. Autoriser la tâche à enregistrer les données : Settings → Actions → General → *Workflow permissions* → *Read and write permissions*.
3. Activer la page : Settings → Pages → *Deploy from a branch* → `main` / `(root)`.
