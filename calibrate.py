"""Génère board_calibration.json en calibrant la grille de trous puis les
couleurs de référence.

Usage :
    python calibrate.py                 # utilise la caméra de Reachy Mini
    python calibrate.py --webcam         # utilise la webcam de l'ordinateur
                                          # (pratique pour tester sans robot)
    python calibrate.py --rows 10 --code-length 4 --colors rouge,bleu,vert,jaune,orange,violet

Déroulé (mode robot réel) :
0. Une fenêtre s'ouvre pour orienter la tête du robot au clavier
   (i/j/k/l) jusqu'à bien cadrer le plateau. 'c'/Entrée pour valider.
1. Une fenêtre s'ouvre avec le flux vidéo en direct.
2. Vous cliquez le centre de chaque trou, ligne par ligne (la ligne 0 sera
   utilisée comme secret en mode codemaker). 'r' pour recommencer une ligne
   ratée, 'q'/Entrée une fois toutes les lignes cliquées.
3. Une seconde fenêtre demande de cliquer un pion de chaque couleur, pour
   calibrer les vraies teintes sous votre éclairage.
4. Le résultat est sauvegardé dans board_calibration.json.

En mode --webcam, l'étape 0 (orientation de la tête) est ignorée : il n'y
a pas de robot à orienter.
"""

import argparse

import cv2

from perception import BoardLayout, calibrate_colors, calibrate_grid
from perception.camera import FakeCamera, ReachyCamera
from robotics import RobotSession, adjust_gaze_interactively

DEFAULT_COLORS = ["rouge", "bleu", "vert", "jaune", "orange", "violet"]
OUTPUT_PATH = "board_calibration.json"


def make_webcam_provider(device_index: int = 0):
    """Fournit une image RGB depuis la webcam locale, pour tester sans robot.

    perception/ suppose des images RGB (format natif du SDK Reachy Mini) ;
    cv2.VideoCapture renvoie du BGR, d'où la conversion.
    """
    cap = cv2.VideoCapture(device_index)
    if not cap.isOpened():
        raise RuntimeError(f"impossible d'ouvrir la webcam #{device_index}")

    def get_frame():
        ok, frame_bgr = cap.read()
        if not ok:
            raise RuntimeError("échec de lecture webcam")
        return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    return get_frame


def calibrate_with_webcam(args, colors) -> BoardLayout:
    with FakeCamera(make_webcam_provider()) as cam:
        print("Étape 1/2 : calibration de la grille de trous.")
        layout = calibrate_grid(cam.get_frame, num_rows=args.rows, code_length=args.code_length)

        print("Étape 2/2 : calibration des couleurs.")
        layout.references = calibrate_colors(cam.get_frame, colors)
    return layout


def calibrate_with_robot(args, colors) -> BoardLayout:
    with RobotSession() as mini:
        # Connexion caméra réutilisant la même session robot (une seule
        # connexion active au total, partagée avec l'orientation de tête).
        with ReachyCamera(mini=mini) as cam:
            print("Étape 0/2 : orientez la tête du robot vers le plateau.")
            adjust_gaze_interactively(mini, cam.get_frame)

            print("Étape 1/2 : calibration de la grille de trous.")
            layout = calibrate_grid(cam.get_frame, num_rows=args.rows, code_length=args.code_length)

            print("Étape 2/2 : calibration des couleurs.")
            layout.references = calibrate_colors(cam.get_frame, colors)
    return layout


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibration du plateau Mastermind")
    parser.add_argument(
        "--webcam", action="store_true",
        help="utiliser la webcam de l'ordinateur au lieu de la caméra Reachy Mini",
    )
    parser.add_argument("--rows", type=int, default=10, help="nombre de lignes du plateau")
    parser.add_argument("--code-length", type=int, default=4, help="nombre de pions par ligne")
    parser.add_argument(
        "--colors", type=str, default=",".join(DEFAULT_COLORS),
        help="couleurs séparées par des virgules, ex: rouge,bleu,vert,jaune",
    )
    args = parser.parse_args()
    colors = args.colors.split(",")

    if args.webcam:
        layout = calibrate_with_webcam(args, colors)
    else:
        layout = calibrate_with_robot(args, colors)

    layout.save(OUTPUT_PATH)
    print(f"Calibration sauvegardée dans {OUTPUT_PATH}")


if __name__ == "__main__":
    main()