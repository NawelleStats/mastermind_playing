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


def _draw_instructions(display, lines: List[str]) -> None:
    """Affiche un panneau lisible de consignes par-dessus l'image live."""
    line_height = 24
    panel_height = 12 + line_height * len(lines)
    cv2.rectangle(display, (6, 6), (650, panel_height), (0, 0, 0), -1)
    for index, line in enumerate(lines):
        cv2.putText(
            display, line, (14, 28 + index * line_height),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1,
            cv2.LINE_AA,
        )


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


def _annotate_rows(
    get_frame,
    rows: List[List[Point]],
    start_row: int,
    end_row: int,
    title: str,
    instructions: List[str],
    num_columns: int,
) -> None:
    """Annote une section de lignes et permet d'annuler le dernier clic."""
    current_row = start_row
    window_name = f"{WINDOW_NAME} - {title}"

    def on_click(event, x, y, flags, param):
        nonlocal current_row
        if event == cv2.EVENT_LBUTTONDOWN and current_row < end_row:
            rows[current_row].append((x, y))
            if len(rows[current_row]) == num_columns:
                current_row += 1

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    cv2.resizeWindow(window_name, 1280, 720)
    cv2.moveWindow(window_name, 40, 40)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
    cv2.setMouseCallback(window_name, on_click)

    while True:
        frame = _read_frame(get_frame)
        display = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR).copy()
        for row in rows:
            for x, y in row:
                cv2.circle(display, (x, y), 6, (0, 255, 0), 2)

        displayed_row = min(current_row, end_row - 1)
        status = f"ligne {displayed_row + 1}/{len(rows)}"
        _draw_instructions(display, instructions + [
            status,
            "R : supprimer le dernier point",
            "Q / Entree : valider cette etape",
        ])
        cv2.imshow(window_name, display)
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

        raw_key = cv2.waitKeyEx(30)
        key = raw_key & 0xFF
        key_char = chr(key).lower() if 0 <= key < 256 else ""
        if key_char == "r":
            for row_index in range(end_row - 1, start_row - 1, -1):
                if rows[row_index]:
                    rows[row_index].pop()
                    current_row = row_index
                    break
        elif key_char == "q" or key in (10, 13):
            if current_row >= end_row:
                break

    cv2.destroyWindow(window_name)


def calibrate_grid(get_frame, num_rows: int, num_columns: int) -> BoardLayout:
    """Calibre d'abord le code secret, puis les lignes restantes du plateau."""
    rows: List[List[Point]] = [[] for _ in range(num_rows)]

    print(f"Étape code secret : cliquez {num_columns} trous sur la ligne 0.")
    _annotate_rows(
        get_frame,
        rows,
        start_row=0,
        end_row=1,
        title="Code secret",
        instructions=[
            "ANNOTATION DU CODE SECRET",
            "Clic gauche : placer un trou du code secret",
            f"Code : {num_columns} trous, de gauche a droite",
        ],
        num_columns=num_columns,
    )

    if num_rows > 1:
        print(f"Étape grille : cliquez les {num_rows - 1} lignes restantes.")
        _annotate_rows(
            get_frame,
            rows,
            start_row=1,
            end_row=num_rows,
            title="Grille",
            instructions=[
                "ANNOTATION DE LA GRILLE",
                "Clic gauche : placer le centre d'un trou",
                f"Grille : {num_rows - 1} lignes restantes x {num_columns} trous",
                "La ligne 0 est deja annotee comme code secret",
            ],
            num_columns=num_columns,
        )

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
            _draw_instructions(display, [
                "CALIBRATION DES COULEURS",
                f"Clic gauche : selectionner un pion {target}",
                "Une couleur a la fois, dans l'ordre affiche",
                "Q : quitter la calibration des couleurs",
            ])
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
