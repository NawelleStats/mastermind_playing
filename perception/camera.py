"""Accès au flux caméra de Reachy Mini.

S'appuie sur l'API officielle du SDK :
    with ReachyMini(media_backend="default") as mini:
        frame = mini.media.get_frame()   # np.ndarray (H, W, 3) uint8, RGB

Ce module isole cette dépendance : le reste de `perception/` ne connaît
que des `np.ndarray`, jamais directement le SDK.
"""

import time
from typing import Generator, Optional

import numpy as np

try:
    from reachy_mini import ReachyMini
except ImportError:  # permet de développer/tester sans le SDK installé
    ReachyMini = None


class ReachyCamera:
    """Contexte gérant la connexion caméra et la cadence de capture.

    Par défaut ouvre sa propre connexion au robot. Si `mini` est fourni
    (ex: une connexion déjà ouverte par `robotics.reachy_client.RobotSession`),
    la réutilise sans la fermer à la sortie du bloc `with` — utile pour
    éviter d'ouvrir plusieurs connexions simultanées à Reachy Mini quand
    perception/robotics/dialogue tournent ensemble.
    """

    def __init__(
        self,
        media_backend: str = "default",
        target_fps: float = 10.0,
        mini: Optional["ReachyMini"] = None,
        fix_channel_swap: bool = True,
    ):
        if mini is None and ReachyMini is None:
            raise RuntimeError(
                "le package 'reachy_mini' n'est pas installé. "
                "pip install reachy-mini pour utiliser la caméra réelle."
            )
        self.media_backend = media_backend
        self.target_fps = target_fps
        self._mini = mini
        self._owns_connection = mini is None
        # Voir `_to_rgb` : `mini.media.get_frame()` renvoie en pratique du
        # BGR sur ce backend, malgré le contrat RGB documenté par le SDK.
        # Passer `fix_channel_swap=False` si une future version du
        # SDK/daemon corrige ce swap en amont (sinon cette correction
        # deviendrait elle-même un bug, en re-swappant des données déjà
        # correctes).
        self.fix_channel_swap = fix_channel_swap

    def __enter__(self) -> "ReachyCamera":
        if self._owns_connection:
            self._mini = ReachyMini(media_backend=self.media_backend).__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._owns_connection and self._mini is not None:
            self._mini.__exit__(exc_type, exc_val, exc_tb)
            self._mini = None

    @staticmethod
    def _to_rgb(frame: np.ndarray) -> np.ndarray:
        """Corrige un swap des canaux rouge/bleu observé sur ce backend.

        Constaté empiriquement sur les données de calibration couleur :
        chaque teinte de référence (rouge, bleu, jaune, orange...)
        atterrissait sur le hue OpenCV de sa couleur *conjuguée* sur le
        cercle chromatique (ex: un pion rouge calibré avec un hue proche
        de celui du bleu), ce qui est la signature typique d'un échange
        R↔B plutôt que d'une balance des blancs. `frame[..., ::-1]`
        inverse l'ordre des canaux ; `np.ascontiguousarray` évite de
        renvoyer une vue à stride négatif que certains appels OpenCV en
        aval n'acceptent pas.
        """
        return np.ascontiguousarray(frame[..., ::-1])

    def get_frame(self, retries: int = 50, retry_delay: float = 0.2) -> np.ndarray:
        """Renvoie la dernière image caméra disponible (RGB, uint8).

        Sur backend WEBRTC (robot distant, cas d'un Reachy Mini wireless),
        les toutes premières frames peuvent arriver vides le temps que la
        négociation vidéo se termine : on réessaie plusieurs fois avant
        d'abandonner plutôt que de planter au premier appel.
        """
        if self._mini is None:
            raise RuntimeError("ReachyCamera utilisé hors du bloc 'with'")

        for attempt in range(retries):
            frame = self._mini.media.get_frame()
            if frame is not None and frame.size > 0:
                if attempt > 0:
                    print(f"[camera] première frame reçue après {attempt} tentative(s)")
                return self._to_rgb(frame) if self.fix_channel_swap else frame
            if attempt == 10:
                print(
                    "[camera] toujours aucune frame après 2s, la négociation "
                    "vidéo WebRTC semble lente ou bloquée..."
                )
            time.sleep(retry_delay)

        raise RuntimeError(
            f"aucune image caméra reçue après {retries} tentatives "
            f"({retries * retry_delay:.1f}s). Causes probables : "
            "(1) désaccord de version SDK/daemon (voir le RuntimeWarning au "
            "démarrage : alignez les deux avec 'pip install reachy-mini==<version du daemon>'), "
            "(2) le flux vidéo n'est pas démarré côté robot."
        )

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
    webcam locale via cv2.VideoCapture). Contrairement à `ReachyCamera`,
    aucune correction de canaux n'est appliquée ici : `make_webcam_provider`
    (dans `calibrate.py`) fait déjà lui-même la conversion BGR->RGB
    nécessaire pour la webcam locale.
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
