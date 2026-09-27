"""Configuration de l'application chargée depuis le fichier .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


_PROJECT_ROOT = Path(__file__).resolve().parent


def _int_setting(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"{name} doit être un entier, reçu : {value!r}") from error


def _path_setting(name: str, default: str) -> str:
    value = os.getenv(name, default)
    path = Path(value)
    return str(path if path.is_absolute() else _PROJECT_ROOT / path)


BOARD_ROWS = _int_setting("BOARD_ROWS", 12)
BOARD_COLUMNS = _int_setting("BOARD_COLUMNS", 5)
MAX_ATTEMPTS = _int_setting("MAX_ATTEMPTS", 10)
COLORS = [
    color.strip()
    for color in os.getenv(
        "COLORS", "rouge,bleu,vert,jaune,orange,marron,noir,blanc"
    ).split(",")
    if color.strip()
]
CALIBRATION_PATH = _path_setting("CALIBRATION_PATH", "board_calibration.json")
REACHY_MINI_HOST = os.getenv("REACHY_MINI_HOST", "reachy-mini.local")
REACHY_MINI_PORT = _int_setting("REACHY_MINI_PORT", 8000)
REACHY_MINI_MEDIA_BACKEND = os.getenv("REACHY_MINI_MEDIA_BACKEND", "default")
REACHY_MINI_CONNECTION_MODE = os.getenv("REACHY_MINI_CONNECTION_MODE", "network")
TTS_VOLUME = float(os.getenv("TTS_VOLUME", "1.0"))
if not 0.0 <= TTS_VOLUME <= 1.0:
    raise ValueError("TTS_VOLUME doit être compris entre 0.0 et 1.0")
