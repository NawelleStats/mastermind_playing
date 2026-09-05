"""Point d'entrée du jeu Mastermind avec Reachy Mini.

Usage :
    python main.py codebreaker   # Reachy Mini devine ton secret
    python main.py codemaker     # Reachy Mini tient le secret, tu devines

Nécessite une calibration préalable (voir perception/calibration.py) et
un fichier `board_calibration.json` à la racine du projet.

La connexion robotique est partagée entre la caméra et le dialogue afin de
n'ouvrir qu'une seule session Reachy Mini.
"""

import sys
import os
from pathlib import Path

from dialogue.dialogue_manager import DialogueManager
from orchestrator import CodebreakerOrchestrator, CodemakerOrchestrator
from perception import BoardLayout
from robotics import RobotSession, go_neutral, look_down_at_board, wake_up

CALIBRATION_PATH = "board_calibration.json"

COLORS = ["rouge", "bleu", "vert", "jaune", "orange", "violet"]
CODE_LENGTH = 4
MAX_ATTEMPTS = 10


def load_layout() -> BoardLayout:
    if not Path(CALIBRATION_PATH).exists():
        sys.exit(
            f"'{CALIBRATION_PATH}' introuvable. Calibrez d'abord le plateau "
            "avec perception.calibration (calibrate_grid + calibrate_colors)."
        )
    return BoardLayout.load(CALIBRATION_PATH)


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("codebreaker", "codemaker"):
        sys.exit("Usage : python main.py [codebreaker|codemaker]")

    mode = sys.argv[1]
    layout = load_layout()

    with RobotSession(
        host=os.getenv("REACHY_MINI_HOST"),
        port=int(os.getenv("REACHY_MINI_PORT", "8000")),
    ) as mini:
        wake_up(mini)
        look_down_at_board(mini)
        dialogue = DialogueManager(mini)
        try:
            if mode == "codebreaker":
                orchestrator = CodebreakerOrchestrator(
                    colors=COLORS,
                    code_length=CODE_LENGTH,
                    max_attempts=MAX_ATTEMPTS,
                    layout=layout,
                    announce_guess=dialogue.announce_guess,
                    on_result=dialogue.on_result,
                    mini=mini,
                )
            else:
                dialogue.announce_ready_for_secret()
                orchestrator = CodemakerOrchestrator(
                    colors=COLORS,
                    code_length=CODE_LENGTH,
                    max_attempts=MAX_ATTEMPTS,
                    layout=layout,
                    announce_feedback=dialogue.announce_feedback,
                    on_result=dialogue.on_result,
                    mini=mini,
                )

            orchestrator.run()
        finally:
            dialogue.close()
            go_neutral(mini)


if __name__ == "__main__":
    main()
