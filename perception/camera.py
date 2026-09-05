"""Accès au flux caméra de Reachy Mini.

S'appuie sur l'API officielle du SDK :
    with ReachyMini(media_backend="default") as mini:
        frame = mini.media.get_frame()   # np.ndarray (H, W, 3) uint8, RGB

Ce module isole cette dépendance : le reste de `perception/` ne connaît
que des `np.ndarray`, jamais directement le SDK.
"""

import os
import time
from typing import Generator, Optional

import numpy as np

try:
    from reachy_mini import ReachyMini
except ImportError:  # permet de développer/tester sans le SDK installé
    ReachyMini = None


class ReachyCamera:
    """Contexte gérant la connexion caméra et la cadence de capture."""

    def __init__(
        self,
        media_backend: str = "default",
        target_fps: float = 10.0,
        mini=None,
        host: Optional[str] = None,
        port: int = 8000,
    ):
        if ReachyMini is None and mini is None:
            raise RuntimeError(
                "le package 'reachy_mini' n'est pas installé. "
                "pip install reachy-mini pour utiliser la caméra réelle."
            )
        self.media_backend = media_backend
        self.host = host
        self.port = port
        self.target_fps = target_fps
        self._mini = mini
        self._owns_mini = mini is None

    def __enter__(self) -> "ReachyCamera":
        if self._owns_mini:
            self._mini = ReachyMini(
                host=self.host or os.getenv("REACHY_MINI_HOST", "reachy-mini.local"),
                port=self.port,
                connection_mode="network",
                spawn_daemon=False,
                media_backend=self.media_backend,
            ).__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._owns_mini and self._mini is not None:
            self._mini.__exit__(exc_type, exc_val, exc_tb)
            self._mini = None

    def get_frame(self) -> np.ndarray:
        """Renvoie la dernière image caméra disponible (RGB, uint8)."""
        if self._mini is None:
            raise RuntimeError("ReachyCamera utilisé hors du bloc 'with'")
        return self._mini.media.get_frame()

    def frames(self) -> Generator[np.ndarray, None, None]:
        """Générateur infini d'images cadencé à `target_fps`.

        Utilisation :
            with ReachyCamera() as cam:
                for frame in cam.frames():
                    ...  # traiter l'image
        """
        period = 1.0 / self.target_fps
        while True:
            t0 = time.monotonic()
            yield self.get_frame()
            elapsed = time.monotonic() - t0
            time.sleep(max(0.0, period - elapsed))


class FakeCamera:
    """Caméra factice pour développer/tester sans robot physique.

    `frame_provider` est une fonction sans argument qui renvoie une image
    np.ndarray à chaque appel (ex: lecture d'un fichier, image statique,
    webcam locale via cv2.VideoCapture).
    """

    def __init__(self, frame_provider, target_fps: float = 10.0):
        self.frame_provider = frame_provider
        self.target_fps = target_fps

    def __enter__(self) -> "FakeCamera":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    def get_frame(self) -> np.ndarray:
        return self.frame_provider()

    def frames(self) -> Generator[np.ndarray, None, None]:
        period = 1.0 / self.target_fps
        while True:
            t0 = time.monotonic()
            yield self.get_frame()
            elapsed = time.monotonic() - t0
            time.sleep(max(0.0, period - elapsed))
