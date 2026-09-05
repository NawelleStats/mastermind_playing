"""Outil de calibration interactif.

Deux étapes à faire une fois, à chaque nouvelle installation du plateau
face à la caméra :

1. `calibrate_grid()`   : cliquer le centre de chaque trou du plateau,
                          ligne par ligne, pour construire une BoardLayout.
2. `calibrate_colors()` : cliquer un pion de chaque couleur pour
                          enregistrer ses valeurs HSV de référence réelles
                          (l'éclairage change la teinte perçue).

Nécessite un affichage (écran connecté à la machine qui exécute ce
script) : ce module n'est pas destiné à tourner "headless" sur le robot.
"""

from typing import List, Tuple

import cv2
import numpy as np
import time

from .color_detector import ColorReference, mean_hsv
from .peg_localizer import BoardLayout, Point

WINDOW_NAME = "Calibration Mastermind"
FRAME_RETRIES = 100
FRAME_RETRY_DELAY = 0.1


def _read_frame(get_frame):
    """Attend la première frame WebRTC valide avant de l'afficher."""
    for attempt in range(FRAME_RETRIES):
        frame = get_frame()
        if isinstance(frame, np.ndarray) and frame.size > 0 and frame.ndim >= 2:
            return frame
        if attempt == 0:
            print("En attente de la première image de la caméra...")
        time.sleep(FRAME_RETRY_DELAY)

    raise RuntimeError(
        "La caméra Reachy ne fournit aucune image valide après "
        f"{FRAME_RETRIES * FRAME_RETRY_DELAY:.1f} secondes. "
        "Vérifiez que le flux caméra est actif et relancez la calibration."
    )


def calibrate_grid(
    get_frame, num_rows: int, code_length: int
) -> BoardLayout:
    """Calibre la grille de trous par clics successifs sur une image live.

    `get_frame` : fonction sans argument renvoyant la dernière image caméra
    (ex: `camera.get_frame`).
    Clique les centres des trous dans l'ordre : ligne 0 gauche→droite, puis
    ligne 1, etc. Appuyer sur 'r' pour recommencer, 'q'/Entrée pour valider
    une fois toutes les lignes cliquées.
    """
    rows: List[List[Point]] = [[] for _ in range(num_rows)]
    current_row = 0

    def on_click(event, x, y, flags, param):
        nonlocal current_row
        if event == cv2.EVENT_LBUTTONDOWN and current_row < num_rows:
            rows[current_row].append((x, y))
            if len(rows[current_row]) == code_length:
                current_row += 1

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    cv2.resizeWindow(WINDOW_NAME, 1280, 720)
    cv2.moveWindow(WINDOW_NAME, 40, 40)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)
    cv2.setMouseCallback(WINDOW_NAME, on_click)

    print(
        f"Calibration grille : cliquez {code_length} trous par ligne, "
        f"pour {num_rows} lignes. 'r' pour réinitialiser, 'q' pour valider."
    )

    while True:
        frame = _read_frame(get_frame)
        display = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR).copy()
        for row in rows:
            for (x, y) in row:
                cv2.circle(display, (x, y), 6, (0, 255, 0), 2)
        status = f"ligne {min(current_row, num_rows - 1) + 1}/{num_rows}"
        cv2.putText(display, status, (10, 24), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 255, 0), 2)
        cv2.imshow(WINDOW_NAME, display)
        cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)

        key = cv2.waitKey(30) & 0xFF
        if key == ord("r"):
            rows = [[] for _ in range(num_rows)]
            current_row = 0
        elif key in (ord("q"), 13) and current_row >= num_rows:
            break

    cv2.destroyWindow(WINDOW_NAME)
    return BoardLayout(rows=rows)


def calibrate_colors(
    get_frame, color_names: List[str], patch_radius: int = 8
) -> dict:
    """Calibre les références HSV réelles en cliquant un pion par couleur.

    Renvoie un dict {nom_couleur: ColorReference} prêt à injecter dans un
    BoardLayout via `layout.references = ...`.
    """
    references = {}
    remaining = list(color_names)
    clicked_point = {"pt": None}

    def on_click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            clicked_point["pt"] = (x, y)

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    cv2.resizeWindow(WINDOW_NAME, 1280, 720)
    cv2.moveWindow(WINDOW_NAME, 40, 40)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)
    cv2.setMouseCallback(WINDOW_NAME, on_click)

    while remaining:
        target = remaining[0]
        print(f"Cliquez un pion de couleur : {target}")

        while clicked_point["pt"] is None:
            frame = _read_frame(get_frame)
            display = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR).copy()
            cv2.putText(display, f"cliquez : {target}", (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow(WINDOW_NAME, display)
            if cv2.waitKey(30) & 0xFF == ord("q"):
                cv2.destroyWindow(WINDOW_NAME)
                return references

        x, y = clicked_point["pt"]
        frame = _read_frame(get_frame)  # RGB natif, format attendu par mean_hsv
        h, w = frame.shape[:2]
        x0, x1 = max(0, x - patch_radius), min(w, x + patch_radius)
        y0, y1 = max(0, y - patch_radius), min(h, y + patch_radius)
        patch = frame[y0:y1, x0:x1]

        hue, sat, val = mean_hsv(patch)
        references[target] = ColorReference(name=target, hue=hue, sat=sat, val=val)
        print(f"  -> {target} : H={hue:.1f} S={sat:.1f} V={val:.1f}")

        remaining.pop(0)
        clicked_point["pt"] = None

    cv2.destroyWindow(WINDOW_NAME)
    return references
