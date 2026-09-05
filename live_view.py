"""Vision en direct du plateau : la fonctionnalité "le robot regarde mon
plateau en temps réel".

Deux usages :
- `run_display(...)` : ouvre une fenêtre affichant le flux caméra avec la
  grille calibrée surimposée et la couleur détectée dans chaque trou.
  Pratique pour vérifier la calibration et voir "avec les yeux du robot".
- `watch_for_new_row(...)` : générateur headless (sans fenêtre) destiné à
  l'orchestrateur : ne renvoie une nouvelle lecture que quand une NOUVELLE
  ligne du plateau vient d'être entièrement remplie, en filtrant le bruit
  par confirmation sur plusieurs frames consécutives.
"""

import time
from typing import Generator, List, Optional, Tuple

import cv2

from .camera import ReachyCamera
from .color_detector import EMPTY_LABEL, UNKNOWN_LABEL
from .peg_localizer import BoardLayout, ClassifyFn, find_last_filled_row, read_row

DISPLAY_WINDOW = "Reachy Mini - vision plateau"


def _color_to_bgr(label: str) -> Tuple[int, int, int]:
    """Couleur d'annotation approximative pour l'overlay (juste visuel)."""
    palette = {
        "rouge": (0, 0, 220), "bleu": (220, 100, 0), "vert": (0, 180, 0),
        "jaune": (0, 220, 220), "orange": (0, 140, 255), "violet": (200, 0, 150),
        EMPTY_LABEL: (120, 120, 120), UNKNOWN_LABEL: (0, 0, 0),
    }
    return palette.get(label, (255, 255, 255))


def run_display(
    layout: BoardLayout, target_fps: float = 10.0, classify_fn: Optional[ClassifyFn] = None
) -> None:
    """Ouvre une fenêtre live avec overlay des couleurs détectées.

    Appuyer sur 'q' pour quitter.
    """
    with ReachyCamera(target_fps=target_fps) as cam:
        for frame in cam.frames():
            display = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR).copy()

            for row_index, row in enumerate(layout.rows):
                colors = read_row(frame, layout, row_index, classify_fn)
                for (x, y), label in zip(row, colors):
                    color = _color_to_bgr(label)
                    cv2.circle(display, (x, y), layout.patch_radius, color, 2)
                    cv2.putText(
                        display, label, (x - 20, y - layout.patch_radius - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1,
                    )

            cv2.imshow(DISPLAY_WINDOW, display)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyWindow(DISPLAY_WINDOW)


def watch_for_new_row(
    layout: BoardLayout,
    already_read_rows: int = 0,
    target_fps: float = 5.0,
    stability_frames: int = 3,
    classify_fn: Optional[ClassifyFn] = None,
) -> Generator[Tuple[int, List[str]], None, None]:
    """Surveille le plateau en continu et cède une lecture uniquement
    quand une nouvelle ligne est détectée comme remplie ET stable
    (identique sur `stability_frames` frames consécutives, pour éviter
    de valider une lecture pendant que l'humain est en train de poser
    les pions).

    `classify_fn` détermine ce qui est lu : couleurs de jeu par défaut
    (utile pour lire le secret ou un essai humain, mode codemaker), ou
    `classify_feedback_patch` pour lire des pions noir/blanc (mode
    codebreaker).

    Cède des tuples (row_index, colors). `already_read_rows` permet de
    reprendre après un redémarrage sans re-signaler des lignes déjà lues.
    """
    last_reported = already_read_rows - 1
    pending: Optional[Tuple[int, List[str]]] = None
    stable_count = 0

    with ReachyCamera(target_fps=target_fps) as cam:
        for frame in cam.frames():
            result = find_last_filled_row(frame, layout, classify_fn)
            if result is None:
                pending, stable_count = None, 0
                continue

            row_index, colors = result
            if row_index <= last_reported:
                continue  # déjà signalée

            if pending is not None and pending == (row_index, colors):
                stable_count += 1
            else:
                pending, stable_count = (row_index, colors), 1

            if stable_count >= stability_frames:
                last_reported = row_index
                pending, stable_count = None, 0
                yield row_index, colors


if __name__ == "__main__":
    # Exemple minimal : suppose une calibration déjà sauvegardée.
    layout = BoardLayout.load("board_calibration.json")
    run_display(layout)
