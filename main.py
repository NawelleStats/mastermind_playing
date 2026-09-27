"""Point d'entrée du jeu Mastermind avec Reachy Mini.

Usage :
    python main.py codebreaker   # Reachy Mini devine ton secret
    python main.py codemaker     # Reachy Mini tient le secret, tu devines

Nécessite une calibration préalable (voir perception/calibration.py) et
un fichier `board_calibration.json` à la racine du projet.

La connexion robotique est partagée entre la caméra et le dialogue afin de
n'ouvrir qu'une seule session Reachy Mini.
"""

import argparse
import sys
from pathlib import Path

from config import (
    CALIBRATION_PATH,
    COLORS,
    MAX_ATTEMPTS,
    REACHY_MINI_CONNECTION_MODE,
    REACHY_MINI_HOST,
    REACHY_MINI_MEDIA_BACKEND,
    REACHY_MINI_PORT,
)
from dialogue.dialogue_manager import DialogueManager
from orchestrator import CodebreakerOrchestrator, CodemakerOrchestrator
from perception import BoardLayout
from robotics import RobotSession, go_neutral, look_down_at_board, wake_up

def load_layout() -> BoardLayout:
    if not Path(CALIBRATION_PATH).exists():
        sys.exit(
            f"'{CALIBRATION_PATH}' introuvable. Calibrez d'abord le plateau "
            "avec perception.calibration (calibrate_grid + calibrate_colors)."
        )
    return BoardLayout.load(CALIBRATION_PATH)


def main() -> None:
    parser = argparse.ArgumentParser(description="Jeu Mastermind avec Reachy Mini")
    parser.add_argument("mode", choices=("codebreaker", "codemaker"))
    parser.add_argument(
        "--show-camera", action="store_true",
        help="afficher ce que la caméra de Reachy voit pendant la partie",
    )
    args = parser.parse_args()

    mode = args.mode
    layout = load_layout()
    colors = list(layout.references) or COLORS
    code_length = layout.code_length

    with RobotSession(
        host=REACHY_MINI_HOST,
        port=REACHY_MINI_PORT,
        media_backend=REACHY_MINI_MEDIA_BACKEND,
        connection_mode=REACHY_MINI_CONNECTION_MODE,
    ) as mini:
        wake_up(mini)
        gaze = layout.gaze or {}
        gaze_pitch_deg = gaze.get("pitch_deg", 25.0)
        gaze_yaw_deg = gaze.get("yaw_deg", 0.0)
        look_down_at_board(
            mini,
            pitch_deg=gaze_pitch_deg,
            yaw_deg=gaze_yaw_deg,
        )
        dialogue = DialogueManager(
            mini,
            gaze_pitch_deg=gaze_pitch_deg,
            gaze_yaw_deg=gaze_yaw_deg,
        )
        try:
            if mode == "codebreaker":
                orchestrator = CodebreakerOrchestrator(
                    colors=colors,
                    code_length=code_length,
                    max_attempts=MAX_ATTEMPTS,
                    layout=layout,
                    announce_guess=dialogue.announce_guess,
                    on_result=dialogue.on_result,
                    show_camera=args.show_camera,
                    mini=mini,
                )
            else:
                dialogue.announce_ready_for_secret()
                orchestrator = CodemakerOrchestrator(
                    colors=colors,
                    code_length=code_length,
                    max_attempts=MAX_ATTEMPTS,
                    layout=layout,
                    announce_feedback=dialogue.announce_feedback,
                    on_result=dialogue.on_result,
                    show_camera=args.show_camera,
                    mini=mini,
                )

            orchestrator.run()
        finally:
            dialogue.close()
            go_neutral(mini)


if __name__ == "__main__":
    main()
