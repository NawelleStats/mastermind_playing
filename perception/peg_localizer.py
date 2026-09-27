"""Localisation spatiale des pions : à partir d'une grille de positions
calibrées (voir calibration.py), extrait un patch d'image à chaque
position et le fait classifier par color_detector.

Le plateau est modélisé comme une grille de "trous" : plusieurs lignes
(une par essai) de N colonnes (la longueur du code). On lit en général
uniquement la dernière ligne remplie par l'humain (feedback en pions
noirs/blancs), Reachy Mini ayant déjà en mémoire son propre essai.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from .color_detector import DEFAULT_REFERENCES, ColorReference, EMPTY_LABEL, classify_patch

Point = Tuple[int, int]  # (x, y) en pixels dans l'image caméra
ClassifyFn = Callable[[np.ndarray], str]


@dataclass
class BoardLayout:
    """Grille de positions de pions calibrée pour un plateau physique donné.

    `rows` : liste de lignes, chaque ligne étant une liste de centres (x, y)
    pour chaque trou de la ligne, dans l'ordre gauche → droite.
    `patch_radius` : demi-taille (en pixels) du carré échantillonné autour
    de chaque centre pour la classification de couleur.
    """
    rows: List[List[Point]] = field(default_factory=list)
    patch_radius: int = 8
    code_length: int = 0
    references: Dict[str, ColorReference] = field(
        default_factory=lambda: DEFAULT_REFERENCES
    )
    gaze: Optional[Dict[str, float]] = None

    def __post_init__(self) -> None:
        if self.rows:
            self.code_length = len(self.rows[0])

    def save(self, path: str) -> None:
        data = {
            "rows": self.rows,
            "patch_radius": self.patch_radius,
            "code_length": self.code_length,
            "references": {
                name: {"hue": r.hue, "sat": r.sat, "val": r.val}
                for name, r in self.references.items()
            },
            "gaze": self.gaze,
        }
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str) -> "BoardLayout":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        references = {
            name: ColorReference(name=name, **vals)
            for name, vals in data["references"].items()
        }
        rows = [[tuple(pt) for pt in row] for row in data["rows"]]
        return cls(
            rows=rows,
            patch_radius=data["patch_radius"],
            references=references,
            gaze=data.get("gaze"),
        )


def _extract_patch(frame: np.ndarray, center: Point, radius: int) -> np.ndarray:
    x, y = center
    h, w = frame.shape[:2]
    x0, x1 = max(0, x - radius), min(w, x + radius)
    y0, y1 = max(0, y - radius), min(h, y + radius)
    return frame[y0:y1, x0:x1]


def read_row(
    frame: np.ndarray,
    layout: BoardLayout,
    row_index: int,
    classify_fn: Optional[ClassifyFn] = None,
    num_columns: Optional[int] = None,
) -> List[str]:
    """Lit une ligne donnée du plateau sur l'image courante.

    `classify_fn` : fonction de classification appliquée à chaque patch.
    Par défaut, classe parmi les couleurs de jeu calibrées (`layout.references`)
    — utile pour lire le secret ou un essai posé par l'humain en mode
    "Reachy Mini codemaker". Pour lire des pions de feedback noir/blanc
    (mode "Reachy Mini codebreaker"), passer `classify_feedback_patch`.
    """
    if row_index >= len(layout.rows):
        raise IndexError(f"row_index {row_index} hors de la grille calibrée")

    fn = classify_fn or (lambda patch: classify_patch(patch, layout.references))
    colors = []
    centers = layout.rows[row_index]
    if num_columns is not None:
        centers = centers[:num_columns]
    for center in centers:
        patch = _extract_patch(frame, center, layout.patch_radius)
        colors.append(fn(patch))
    return colors


def find_last_filled_row(
    frame: np.ndarray,
    layout: BoardLayout,
    classify_fn: Optional[ClassifyFn] = None,
    num_columns: Optional[int] = None,
) -> Optional[Tuple[int, List[str]]]:
    """Parcourt les lignes de haut en bas et renvoie la dernière ligne
    entièrement remplie (aucun trou EMPTY_LABEL), avec son index et son
    contenu classifié selon `classify_fn` (voir `read_row`).

    Utile pour détecter automatiquement quand une nouvelle ligne du
    plateau vient d'être remplie, sans devoir demander de confirmation
    vocale.
    """
    last_filled = None
    for i in range(len(layout.rows)):
        colors = read_row(frame, layout, i, classify_fn, num_columns)
        if EMPTY_LABEL not in colors:
            last_filled = (i, colors)
        else:
            break
    return last_filled
