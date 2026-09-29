"""Assemble voix et gestes en réactions cohérentes aux événements de jeu.

Expose directement les callbacks attendus par `orchestrator.game_fsm`
(`announce_guess`, `announce_feedback`, `on_result`), pour un branchement
en une ligne dans `main.py` — voir le TODO qui y était laissé.
"""

from typing import List

from core.rules import Feedback
from robotics import (
    express_disappointment,
    express_joy,
    look_down_at_board,
    nod_yes,
    thinking,
    wiggle_antennas,
)
from .text_to_speech import Speaker


class DialogueManager:
    """Point d'entrée unique pour les réactions vocales + gestuelles.

    `mini` doit être une connexion déjà ouverte, partagée avec le reste de
    l'application (voir `robotics.RobotSession`).
    """

    def __init__(
        self,
        mini,
        language_hint: str = "fr",
        gaze_pitch_deg: float = 25.0,
        gaze_yaw_deg: float = 0.0,
        gaze_height_m: float | None = None,
    ):
        self._mini = mini
        self._gaze_pitch_deg = gaze_pitch_deg
        self._gaze_yaw_deg = gaze_yaw_deg
        self._gaze_height_m = gaze_height_m
        self._speaker = Speaker(mini, voice_lang_hint=language_hint)

    # --- Mode codebreaker : Reachy Mini propose ses essais -----------------

    def announce_guess(self, guess: List[str]) -> None:
        thinking(self._mini)
        look_down_at_board(
            self._mini,
            pitch_deg=self._gaze_pitch_deg,
            yaw_deg=self._gaze_yaw_deg,
            height_m=self._gaze_height_m,
        )
        self._speaker.say(f"Je propose : {', '.join(guess)}.")

    # --- Mode codemaker : Reachy Mini note les essais de l'humain -----------

    def announce_feedback(self, guess: List[str], feedback: Feedback) -> None:
        if feedback.black == 0 and feedback.white == 0:
            wiggle_antennas(self._mini)
        phrase = self._feedback_phrase(feedback)
        self._speaker.say(phrase)
        if feedback.black > 0:
            nod_yes(self._mini, repetitions=1)

    @staticmethod
    def _feedback_phrase(feedback: Feedback) -> str:
        black = f"{feedback.black} pion noir" + ("s" if feedback.black != 1 else "")
        white = f"{feedback.white} pion blanc" + ("s" if feedback.white != 1 else "")
        if feedback.black == 0 and feedback.white == 0:
            return "Aucun pion bien placé, ni aucune bonne couleur."
        return f"{black} et {white}."

    # --- Commun aux deux modes ----------------------------------------------

    def on_result(self, won: bool) -> None:
        if won:
            self._speaker.say("Trouvé ! J'ai gagné cette manche.")
            express_joy(self._mini)
        else:
            self._speaker.say("Je n'ai pas trouvé à temps, tu as gagné cette manche.")
            express_disappointment(self._mini)

    def announce_ready_for_secret(self) -> None:
        self._speaker.say("Place ta combinaison secrète, je ne regarde pas encore.")

    def close(self) -> None:
        self._speaker.close()
