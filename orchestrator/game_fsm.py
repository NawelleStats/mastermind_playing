"""Orchestrateur de partie : coordonne core, perception, robotics et
dialogue selon le rôle joué par Reachy Mini.

Deux modes, deux classes distinctes plutôt qu'un gros if/else :

- `CodebreakerOrchestrator` : Reachy Mini devine. Il propose les essais
  (via `solver.Solver`), l'humain place le secret et répond par des pions
  noir/blanc que la caméra lit (`classify_feedback_patch`).

- `CodemakerOrchestrator` : Reachy Mini tient le secret. L'humain place la
  combinaison secrète à l'aveugle sur la ligne 0 du plateau ; la caméra la
  lit une seule fois (couleurs de jeu, `classify_patch`) et Reachy Mini ne
  la révèle jamais à voix haute. Chaque ligne suivante est un essai de
  l'humain, lu par la même caméra ; Reachy Mini calcule et annonce
  uniquement le score noir/blanc.

Les deux réutilisent le même mécanisme bas niveau (`watch_for_new_row`,
une ligne du plateau = un tour), seul `classify_fn` et l'interprétation
du flux changent.
"""

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from core import Board, Solver
from core.codemaker import validate_guess
from core.rules import Feedback
from perception import (
    BoardLayout,
    classify_feedback_patch,
    classify_patch,
    watch_for_new_row,
)

AnnounceGuess = Callable[[List[str]], None]
AnnounceFeedback = Callable[[List[str], Feedback], None]
OnResult = Callable[[bool], None]


def _default_on_result(won: bool) -> None:
    print("Gagné !" if won else "Perdu — le nombre d'essais maximum est atteint.")


def labels_to_feedback(labels: List[str]) -> Feedback:
    """Convertit une liste de labels noir/blanc/vide en score Mastermind.

    L'ORDRE des pions de feedback n'a pas de sens en Mastermind classique
    (seul le compte importe) : on se contente de compter.
    """
    return Feedback(black=labels.count("noir"), white=labels.count("blanc"))


@dataclass
class CodebreakerOrchestrator:
    """Reachy Mini devine le secret placé par l'humain."""

    colors: List[str]
    code_length: int
    max_attempts: int
    layout: BoardLayout
    announce_guess: AnnounceGuess = print
    on_result: OnResult = _default_on_result
    camera_fps: float = 5.0
    stability_frames: int = 3
    mini: object = None

    def run(self) -> Board:
        board = Board(
            colors=self.colors, code_length=self.code_length,
            max_attempts=self.max_attempts, secret=None,
        )
        solver = Solver(self.colors, self.code_length)

        feedback_stream = watch_for_new_row(
            self.layout, already_read_rows=0, target_fps=self.camera_fps,
            stability_frames=self.stability_frames, classify_fn=classify_feedback_patch,
            mini=self.mini,
        )

        for _ in range(self.max_attempts):
            guess = solver.next_guess()
            self.announce_guess(guess)

            _, labels = next(feedback_stream)
            feedback = labels_to_feedback(labels)
            board.record_feedback(guess, feedback)
            solver.update(guess, feedback)

            if board.is_won:
                break

        self.on_result(board.is_won)
        return board


@dataclass
class CodemakerOrchestrator:
    """Reachy Mini tient le secret (perçu par caméra) et note les essais
    de l'humain."""

    colors: List[str]
    code_length: int
    max_attempts: int
    layout: BoardLayout
    announce_feedback: AnnounceFeedback = lambda guess, fb: print(
        f"essai {guess} -> noirs={fb.black} blancs={fb.white}"
    )
    on_result: OnResult = _default_on_result
    camera_fps: float = 5.0
    stability_frames: int = 3
    mini: object = None

    def run(self) -> Board:
        stream = watch_for_new_row(
            self.layout, already_read_rows=0, target_fps=self.camera_fps,
            stability_frames=self.stability_frames, classify_fn=classify_patch,
            mini=self.mini,
        )

        # Ligne 0 : le secret, placé à l'aveugle par l'humain.
        _, secret = next(stream)
        validate_guess(secret, self.colors, self.code_length)

        board = Board(
            colors=self.colors, code_length=self.code_length,
            max_attempts=self.max_attempts, secret=secret,
        )

        for _ in range(self.max_attempts):
            _, guess = next(stream)
            validate_guess(guess, self.colors, self.code_length)
            feedback = board.play(guess)
            self.announce_feedback(guess, feedback)

            if board.is_won:
                break

        self.on_result(board.is_won)
        return board
