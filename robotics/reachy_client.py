"""Connexion partagée à Reachy Mini.

Un seul `RobotSession` doit être ouvert par exécution de `main.py`, puis
son `.mini` partagé avec `perception.ReachyCamera(mini=...)`,
`dialogue.Speaker(mini=...)` etc., pour n'avoir qu'une connexion active
au robot à la fois.
"""

import os
from typing import Any, Optional

import numpy as np

try:
    from reachy_mini import ReachyMini
    from reachy_mini.utils import create_head_pose
except ImportError:  # permet de développer/tester sans le SDK installé
    ReachyMini = None
    create_head_pose = None

NEUTRAL_DURATION = 1.0


class RobotSession:
    """Ouvre et referme la connexion unique au robot physique."""

    def __init__(
        self,
        media_backend: str = "default",
        host: Optional[str] = None,
        port: int = 8000,
        connection_mode: str = "network",
    ):
        if ReachyMini is None:
            raise RuntimeError(
                "le package 'reachy_mini' n'est pas installé. "
                "pip install reachy-mini pour piloter le robot réel."
            )
        self.media_backend = media_backend
        self.host = host or os.getenv("REACHY_MINI_HOST", "reachy-mini.local")
        self.port = port
        self.connection_mode = connection_mode
        self.mini: Optional[Any] = None

    def __enter__(self) -> Any:
        self.mini = ReachyMini(
            host=self.host,
            port=self.port,
            connection_mode=self.connection_mode,
            spawn_daemon=False,
            media_backend=self.media_backend,
        ).__enter__()
        return self.mini

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.mini is not None:
            self.mini.__exit__(exc_type, exc_val, exc_tb)
            self.mini = None


def go_neutral(mini, duration: float = NEUTRAL_DURATION) -> None:
    """Position neutre : tête droite, antennes au repos, corps face au plateau."""
    mini.goto_target(
        head=create_head_pose(),
        antennas=np.deg2rad([0, 0]),
        body_yaw=0.0,
        duration=duration,
        method="minjerk",
    )


def look_down_at_board(mini, pitch_deg: float = 25.0, duration: float = 1.0) -> None:
    """Incline la tête vers le bas, posture d'observation du plateau posé
    devant le robot. `pitch_deg` est à ajuster selon la hauteur du plateau.
    """
    mini.goto_target(
        head=create_head_pose(pitch=pitch_deg, degrees=True),
        duration=duration,
        method="minjerk",
    )


def look_at_pixel(mini, u: float, v: float, duration: float = 0.8) -> None:
    """Fait regarder le robot vers un pixel de sa propre image caméra.

    Pratique pour "pointer du regard" une case du plateau : réutilise
    directement les coordonnées (x, y) d'un `BoardLayout` calibré, sans
    calibration angle/caméra séparée.
    """
    mini.look_at_image(u, v, duration=duration)


def wake_up(mini) -> None:
    """Comportement intégré du SDK : pose d'initialisation + son. Utile en
    tout début de partie."""
    mini.wake_up()


def go_to_sleep(mini) -> None:
    """Comportement intégré du SDK : pose de veille + son. Utile en fin de
    session (pas nécessairement en fin de partie)."""
    mini.goto_sleep()


def adjust_gaze_interactively(
    mini,
    get_frame,
    initial_pitch_deg: float = 25.0,
    initial_yaw_deg: float = 0.0,
    step_deg: float = 3.0,
) -> None:
    """Ouvre une fenêtre live permettant d'orienter la tête au clavier
    jusqu'à bien cadrer le plateau, avant de lancer la calibration.

    Touches (lettres, pas les flèches : leur code varie trop selon l'OS
    dans OpenCV, notamment sur macOS) :
        i / k : pencher la tête vers le haut / le bas (pitch)
        j / l : tourner la tête à gauche / à droite (yaw)
        +  /  - : augmenter / diminuer le pas de déplacement
        c ou Entrée : valider la position et continuer
        q : passer sans changer la position par défaut
    """
    import cv2

    pitch, yaw, step = initial_pitch_deg, initial_yaw_deg, step_deg
    window = "Ajuster le regard du robot"
    cv2.namedWindow(window)

    def apply_pose() -> None:
        mini.goto_target(
            head=create_head_pose(pitch=pitch, yaw=yaw, degrees=True), duration=0.3
        )

    apply_pose()
    print(
        "Orientez la tête du robot pour bien cadrer le plateau : "
        "i/k = haut/bas, j/l = gauche/droite, +/- = pas, "
        "c ou Entrée = valider, q = passer."
    )

    while True:
        frame = get_frame()
        display = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR).copy()
        cv2.putText(
            display, f"pitch={pitch:.0f} yaw={yaw:.0f} pas={step:.0f}",
            (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2,
        )
        cv2.imshow(window, display)

        key = cv2.waitKey(30) & 0xFF
        moved = True
        if key == ord("i"):
            pitch -= step
        elif key == ord("k"):
            pitch += step
        elif key == ord("j"):
            yaw -= step
        elif key == ord("l"):
            yaw += step
        elif key == ord("+"):
            step += 1.0
            moved = False
        elif key == ord("-"):
            step = max(1.0, step - 1.0)
            moved = False
        elif key in (ord("c"), 13):
            break
        elif key == ord("q"):
            break
        else:
            moved = False

        if moved:
            apply_pose()

    cv2.destroyWindow(window)