"""Stratégie de résolution pour Reachy Mini en tant que codebreaker.

Implémente une version simplifiée de l'algorithme minimax de Knuth :
à chaque tour, on garde uniquement les hypothèses de secret compatibles
avec tout l'historique de feedback, puis on choisit le prochain essai qui
minimise le pire cas restant (le nombre maximal d'hypothèses qui
resteraient possibles quel que soit le feedback obtenu).

Pour un plateau standard (6 couleurs, longueur 4), l'espace des hypothèses
fait 6**4 = 1296 combinaisons : largement gérable en calcul brut.
"""

import itertools
from typing import List, Sequence, Tuple

from .rules import Feedback, compute_feedback


class Solver:
    """Solveur incrémental : conserve les hypothèses compatibles au fil du jeu."""

    def __init__(self, colors: Sequence[str], code_length: int):
        self.colors = list(colors)
        self.code_length = code_length
        self.candidates: List[Tuple[str, ...]] = list(
            itertools.product(self.colors, repeat=code_length)
        )

    def next_guess(self) -> List[str]:
        """Retourne le prochain essai à jouer.

        Premier coup : heuristique fixe (ex. deux paires de couleurs
        distinctes) plutôt qu'un calcul minimax coûteux sur l'espace complet.
        Coups suivants : minimax sur les candidats restants.
        """
        if len(self.candidates) == len(
            list(itertools.product(self.colors, repeat=self.code_length))
        ):
            return self._opening_guess()
        return list(self._minimax_best_guess())

    def update(self, guess: Sequence[str], feedback: Feedback) -> None:
        """Filtre les hypothèses incompatibles avec le feedback observé."""
        guess_t = tuple(guess)
        self.candidates = [
            c for c in self.candidates if compute_feedback(c, guess_t) == feedback
        ]

    def _opening_guess(self) -> List[str]:
        """Premier essai raisonnable : répartit les couleurs sans calcul lourd."""
        base = self.colors * ((self.code_length // len(self.colors)) + 1)
        pattern = []
        for i in range(self.code_length):
            pattern.append(base[i // 2 % len(self.colors)])
        return pattern[: self.code_length]

    def _minimax_best_guess(self) -> Tuple[str, ...]:
        """Choisit le candidat qui minimise le pire cas parmi tous les
        feedbacks possibles (heuristique de Knuth).
        """
        best_guess = None
        best_worst_case = None

        # On peut tester tout l'espace des couleurs (pas seulement les
        # candidats restants) pour de meilleurs coups, mais se limiter aux
        # candidats restants est nettement plus rapide et reste efficace.
        for guess in self.candidates:
            partitions: dict[Feedback, int] = {}
            for secret in self.candidates:
                fb = compute_feedback(secret, guess)
                partitions[fb] = partitions.get(fb, 0) + 1
            worst_case = max(partitions.values())

            if best_worst_case is None or worst_case < best_worst_case:
                best_worst_case = worst_case
                best_guess = guess

        assert best_guess is not None
        return best_guess

    @property
    def remaining_candidates(self) -> int:
        return len(self.candidates)
