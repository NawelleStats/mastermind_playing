# Journal des changements

## 2026-09-29

- Ajout de la possibilité d'ajuster la tête en montant et descendant, pour avoir une vision plongeante.

## 2026-09-27

- Correction des couleurs lors de l'affichage de la perception du robot (BGR au lieu de RGB).
- Utilisation des variables d'environnement gérées par config.py.
- Amélioration de la calibration (notamment sur les mouvements de tête), ajout d'un texte 
Uindicatif lors des différentes étapes.
- Affichage en temps réel lorsque la partie est en cours.
- Amélioration de la partie vocale.

TODO: améliorer la logique du jeu

## 2026-09-21

- Ajout d'une configuration centralisée via `.env` pour les dimensions du
	plateau, la longueur du code, les couleurs, les essais et la connexion
	Reachy Mini.
- Paramétrage de la grille.
- Séparation de l'annotation de la ligne du code secret et de la grille.
- La touche `R` supprime uniquement le dernier point annoté.
- Ajout de `pyproject.toml` et des instructions `uv sync` / `uv run` pour
	gérer l'environnement virtuel et les dépendances.
