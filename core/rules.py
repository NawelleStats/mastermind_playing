"""Règles du jeu Mastermind : calcul du feedback pour un essai donné."""

from collections import Counter
from typing import NamedTuple, Sequence


class Feedback(NamedTuple):
    """Résultat de comparaison entre un essai et le code secret."""
    black: int  # bonne couleur, bonne position
    white: int  # bonne couleur, mauvaise position

    @property
    def is_win(self) -> bool:
        return self.white == 0 and self.black > 0  # affiné dans compute_feedback


def compute_feedback(secret: Sequence[str], guess: Sequence[str]) -> Feedback:
    """Calcule le nombre de pions noirs et blancs pour un essai.

    - Un pion noir : couleur ET position correctes.
    - Un pion blanc : couleur présente dans le secret mais mal placée.

    Les deux séquences doivent avoir la même longueur.
    """
    if len(secret) != len(guess):
        raise ValueError("secret et guess doivent avoir la même longueur")

    black = sum(s == g for s, g in zip(secret, guess))

    # Pour les blancs : on compte les couleurs en commun (hors positions déjà
    # comptées en noir), en respectant les doublons via Counter.
    secret_remaining = Counter(s for s, g in zip(secret, guess) if s != g)
    guess_remaining = Counter(g for s, g in zip(secret, guess) if s != g)
    white = sum(min(secret_remaining[c], guess_remaining[c]) for c in guess_remaining)

    return Feedback(black=black, white=white)


def is_winning_feedback(feedback: Feedback, code_length: int) -> bool:
    """Un essai gagne quand tous les pions sont noirs."""
    return feedback.black == code_length
