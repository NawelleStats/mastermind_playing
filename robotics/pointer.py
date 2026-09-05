"""Pointage : faire regarder Reachy Mini vers une case précise du plateau.

S'appuie sur `mini.look_at_image(u, v)`, qui accepte directement des
coordonnées pixel de l'image caméra — les mêmes que celles calibrées dans
un `perception.BoardLayout`. Aucune calibration angle/caméra séparée
n'est nécessaire.
"""

from typing import List, Optional, Sequence, Tuple

from .reachy_client import look_at_pixel

Point = Tuple[int, int]


def point_at_slot(mini, center: Point, duration: float = 0.8) -> None:
    """Regarde vers un trou précis du plateau (centre pixel calibré)."""
    u, v = center
    look_at_pixel(mini, u, v, duration=duration)


def point_at_guess(
    mini,
    row_centers: Sequence[Point],
    pause_between: float = 0.4,
    duration_per_slot: float = 0.6,
) -> None:
    """Balaie du regard chaque case d'une ligne, dans l'ordre — utile pour
    accompagner visuellement l'annonce vocale d'un essai (mode codebreaker).
    """
    import time

    for center in row_centers:
        point_at_slot(mini, center, duration=duration_per_slot)
        time.sleep(pause_between)


def find_color_center(
    layout_row: Sequence[Point], colors_in_row: Sequence[str], target_color: str
) -> Optional[Point]:
    """Retrouve le centre pixel de la première occurrence d'une couleur
    donnée dans une ligne déjà lue (colors_in_row vient de `read_row`).
    """
    for center, color in zip(layout_row, colors_in_row):
        if color == target_color:
            return center
    return None
