"""Détection de couleur : classe un patch d'image parmi des couleurs de
référence calibrées, en travaillant dans l'espace HSV (plus robuste aux
variations d'éclairage que le RGB brut).
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import cv2
import numpy as np


@dataclass
class ColorReference:
    """Couleur de référence calibrée, en HSV OpenCV (H:0-179, S/V:0-255)."""
    name: str
    hue: float
    sat: float
    val: float


# Valeurs par défaut raisonnables pour des pions Mastermind classiques.
# À RECALIBRER avec calibration.py selon l'éclairage réel du plateau.
DEFAULT_REFERENCES: Dict[str, ColorReference] = {
    "rouge":  ColorReference("rouge", hue=0,   sat=200, val=180),
    "bleu":   ColorReference("bleu", hue=110,  sat=200, val=180),
    "vert":   ColorReference("vert", hue=60,   sat=180, val=170),
    "jaune":  ColorReference("jaune", hue=28,  sat=200, val=200),
    "orange": ColorReference("orange", hue=14, sat=210, val=200),
    "violet": ColorReference("violet", hue=145, sat=150, val=150),
}

EMPTY_LABEL = "vide"          # aucun pion détecté dans le trou
UNKNOWN_LABEL = "inconnu"      # couleur ne matchant aucune référence

# Seuils pour distinguer "trou vide" (fond du plateau, souvent peu saturé)
# d'un pion coloré. À ajuster selon le plateau utilisé.
MIN_SATURATION_FOR_PEG = 60
MIN_VALUE_FOR_PEG = 40


def _hue_distance(h1: float, h2: float) -> float:
    """Distance circulaire entre deux teintes OpenCV (modulo 180)."""
    d = abs(h1 - h2)
    return min(d, 180 - d)


def classify_patch(
    patch_rgb: np.ndarray,
    references: Optional[Dict[str, ColorReference]] = None,
) -> str:
    """Classe un patch d'image (petite zone RGB, format natif du SDK Reachy
    Mini) parmi les couleurs connues.

    Renvoie le nom de la couleur la plus proche, EMPTY_LABEL si le patch
    semble être un trou vide (faible saturation/valeur), ou UNKNOWN_LABEL
    si aucune référence n'est suffisamment proche.
    """
    references = references or DEFAULT_REFERENCES

    hsv = cv2.cvtColor(patch_rgb, cv2.COLOR_RGB2HSV)
    mean_h, mean_s, mean_v = hsv.reshape(-1, 3).mean(axis=0)

    if mean_s < MIN_SATURATION_FOR_PEG or mean_v < MIN_VALUE_FOR_PEG:
        return EMPTY_LABEL

    best_name, best_dist = None, float("inf")
    for ref in references.values():
        dist = _hue_distance(mean_h, ref.hue)
        if dist < best_dist:
            best_name, best_dist = ref.name, dist

    # Tolérance de teinte : au-delà, on ne fait pas confiance au match.
    MAX_HUE_DISTANCE = 20
    if best_dist > MAX_HUE_DISTANCE:
        return UNKNOWN_LABEL
    return best_name


def mean_hsv(patch_rgb: np.ndarray) -> Tuple[float, float, float]:
    """Utilitaire pour la calibration : teinte/saturation/valeur moyennes."""
    hsv = cv2.cvtColor(patch_rgb, cv2.COLOR_RGB2HSV)
    h, s, v = hsv.reshape(-1, 3).mean(axis=0)
    return float(h), float(s), float(v)


# --- Feedback (pions noirs/blancs) -----------------------------------------
# Ces pions sont non saturés par construction (gris foncé/clair), donc
# `classify_patch` les confondrait avec un trou vide (même critère : faible
# saturation). Il faut un classifieur séparé basé sur la luminosité (V).
# À recalibrer avec calibration.py selon l'éclairage réel du plateau.
FEEDBACK_BLACK_MAX_VALUE = 70    # en dessous : pion noir
FEEDBACK_WHITE_MIN_VALUE = 170   # au-dessus (+ peu saturé) : pion blanc
FEEDBACK_WHITE_MAX_SATURATION = 60

BLACK_LABEL = "noir"
WHITE_LABEL = "blanc"


def classify_feedback_patch(patch_rgb: np.ndarray) -> str:
    """Classe un patch parmi noir / blanc / vide, pour lire les pions de
    feedback que l'humain place en réponse à l'essai de Reachy Mini.
    """
    hsv = cv2.cvtColor(patch_rgb, cv2.COLOR_RGB2HSV)
    _, mean_s, mean_v = hsv.reshape(-1, 3).mean(axis=0)

    if mean_v < FEEDBACK_BLACK_MAX_VALUE:
        return BLACK_LABEL
    if mean_v > FEEDBACK_WHITE_MIN_VALUE and mean_s < FEEDBACK_WHITE_MAX_SATURATION:
        return WHITE_LABEL
    return EMPTY_LABEL
