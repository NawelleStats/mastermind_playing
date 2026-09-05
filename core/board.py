"""Représentation de l'état du plateau de jeu et de son historique."""

from dataclasses import dataclass, field
from typing import List, Sequence

from .rules import Feedback, compute_feedback, is_winning_feedback


@dataclass
class Attempt:
    """Un essai joué avec son feedback associé."""
    guess: List[str]
    feedback: Feedback


@dataclass
class Board:
    """Plateau de jeu : configuration + historique des essais."""

    colors: List[str]              # ex: ["rouge", "bleu", "vert", "jaune", "orange", "violet"]
    code_length: int = 4
    max_attempts: int = 10
    secret: List[str] | None = None  # None si le secret n'est pas connu du programme
    history: List[Attempt] = field(default_factory=list)

    def play(self, guess: Sequence[str]) -> Feedback:
        """Joue un essai contre le secret connu et enregistre le résultat.

        À n'utiliser que si `self.secret` est défini (ex: mode test, ou
        Reachy Mini codemaker). Si le secret est tenu par un humain, le
        feedback est fourni séparément via `record_feedback`.
        """
        if self.secret is None:
            raise RuntimeError("Aucun secret connu : utilisez record_feedback()")
        feedback = compute_feedback(self.secret, list(guess))
        self.history.append(Attempt(guess=list(guess), feedback=feedback))
        return feedback

    def record_feedback(self, guess: Sequence[str], feedback: Feedback) -> None:
        """Enregistre un essai et un feedback fournis par une source externe
        (ex: perception caméra ou saisie vocale de l'humain codemaker).
        """
        self.history.append(Attempt(guess=list(guess), feedback=feedback))

    @property
    def attempts_used(self) -> int:
        return len(self.history)

    @property
    def attempts_left(self) -> int:
        return self.max_attempts - self.attempts_used

    @property
    def is_won(self) -> bool:
        return bool(self.history) and is_winning_feedback(
            self.history[-1].feedback, self.code_length
        )

    @property
    def is_lost(self) -> bool:
        return not self.is_won and self.attempts_left <= 0

    @property
    def is_over(self) -> bool:
        return self.is_won or self.is_lost

    def reset(self) -> None:
        self.history.clear()
        self.secret = None
