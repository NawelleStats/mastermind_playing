"""Connexion partagée à Reachy Mini.

Un seul `RobotSession` doit être ouvert par exécution de `main.py`, puis
son `.mini` partagé avec `perception.ReachyCamera(mini=...)`,
`dialogue.Speaker(mini=...)` etc., pour n'avoir qu'une connexion active
au robot à la fois.
"""

from typing import Any, Optional

import numpy as np

from config import (
    REACHY_MINI_CONNECTION_MODE,
    REACHY_MINI_HOST,
    REACHY_MINI_MEDIA_BACKEND,
    REACHY_MINI_PORT,
)

try:
    from reachy_mini import ReachyMini
    from reachy_mini.utils import create_head_pose
except ImportError:  # permet de développer/tester sans le SDK installé
    ReachyMini = None
    create_head_pose = None

NEUTRAL_DURATION = 1.0

# Pitch : limite matérielle directe de la tête, [-40, +40]°.
GAZE_PITCH_RANGE_DEG = (-40.0, 40.0)
# Yaw : la tête seule tolère [-180, +180]° côté matériel, mais la
# contrainte réelle est le delta head/body (max 65°). Le yaw admissible
# dépend donc du yaw actuel du corps et se calcule dynamiquement — voir
# `_dynamic_gaze_yaw_range_deg` ci-dessous — plutôt que d'être une
# constante figée en supposant un corps immobile à 0°.
HEAD_YAW_HW_RANGE_DEG = (-180.0, 180.0)
MAX_HEAD_BODY_YAW_DELTA_DEG = 65.0
GAZE_STEP_RANGE_DEG = (1.0, 15.0)


def _get_body_yaw_deg(mini) -> Optional[float]:
    """Tente de récupérer le yaw actuel du corps, en degrés.

    Le nom exact de l'accesseur peut varier selon la version du SDK
    Python (voir `docs/source/SDK/python-sdk.md`) : on essaie ici les
    noms les plus plausibles et on renvoie `None` si aucun ne fonctionne,
    pour dégrader proprement plutôt que planter. À ajuster si le SDK
    expose un nom différent.
    """
    for attr in ("get_current_body_yaw", "get_body_yaw", "body_yaw"):
        candidate = getattr(mini, attr, None)
        if candidate is None:
            continue
        try:
            value = candidate() if callable(candidate) else candidate
            return float(np.rad2deg(value))
        except Exception:
            continue
    return None


def _dynamic_gaze_yaw_range_deg(mini) -> tuple:
    """Calcule la plage de yaw admissible pour la tête, en tenant compte
    du yaw *actuel* du corps plutôt que de supposer un corps immobile à 0°.

    Combine la limite matérielle de la tête (`HEAD_YAW_HW_RANGE_DEG`) et la
    contrainte de delta head/body (`MAX_HEAD_BODY_YAW_DELTA_DEG`) ; la plus
    stricte des deux s'applique à chaque borne.
    """
    body_yaw_deg = _get_body_yaw_deg(mini)
    if body_yaw_deg is None:
        print(
            "Attention : yaw du corps introuvable via le SDK, "
            "hypothèse corps à 0° utilisée pour borner le yaw de la tête."
        )
        body_yaw_deg = 0.0
    lo = max(HEAD_YAW_HW_RANGE_DEG[0], body_yaw_deg - MAX_HEAD_BODY_YAW_DELTA_DEG)
    hi = min(HEAD_YAW_HW_RANGE_DEG[1], body_yaw_deg + MAX_HEAD_BODY_YAW_DELTA_DEG)
    return (lo, hi)


class RobotSession:
    """Ouvre et referme la connexion unique au robot physique."""

    def __init__(
        self,
        media_backend: str = REACHY_MINI_MEDIA_BACKEND,
        host: Optional[str] = None,
        port: int = REACHY_MINI_PORT,
        connection_mode: str = REACHY_MINI_CONNECTION_MODE,
    ):
        if ReachyMini is None:
            raise RuntimeError(
                "le package 'reachy_mini' n'est pas installé. "
                "pip install reachy-mini pour piloter le robot réel."
            )
        self.media_backend = media_backend
        self.host = host or REACHY_MINI_HOST
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

    def __exit__(self, exc_type, exc_val, exc_tb) -> Optional[bool]:
        if self.mini is None:
            return None
        try:
            # On propage la valeur de retour : si le SDK choisit d'avaler
            # une exception (retour vérité), ce wrapper doit le respecter
            # plutôt que de la masquer silencieusement.
            return self.mini.__exit__(exc_type, exc_val, exc_tb)
        finally:
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


def look_down_at_board(
    mini, pitch_deg: float = 25.0, yaw_deg: float = 0.0, duration: float = 1.0
) -> None:
    """Incline la tête vers le bas, posture d'observation du plateau posé
    devant le robot. `pitch_deg` est à ajuster selon la hauteur du plateau.
    """
    current_pose = np.asarray(mini.get_current_head_pose(), dtype=float)
    head_position = current_pose[:3, 3]
    mini.goto_target(
        head=create_head_pose(
            x=head_position[0],
            y=head_position[1],
            z=head_position[2],
            pitch=pitch_deg,
            yaw=yaw_deg,
            degrees=True,
        ),
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


def _clamp(value: float, bounds: tuple) -> float:
    lo, hi = bounds
    return max(lo, min(hi, value))


def _is_enter_key(key: int) -> bool:
    return (key & 0xFF) in (10, 13)


def adjust_gaze_interactively(
    mini,
    get_frame,
    initial_pitch_deg: float = 0.0,
    initial_yaw_deg: float = 0.0,
    step_deg: float = 3.0,
) -> tuple[float, float]:
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
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError(
            "opencv-python est requis pour l'ajustement interactif du "
            "regard (pip install opencv-python)."
        ) from exc

    gaze_yaw_range_deg = _dynamic_gaze_yaw_range_deg(mini)

    pitch = _clamp(initial_pitch_deg, GAZE_PITCH_RANGE_DEG)
    yaw = _clamp(initial_yaw_deg, gaze_yaw_range_deg)
    step = _clamp(step_deg, GAZE_STEP_RANGE_DEG)
    last_command = "aucune"
    window = "Ajuster le regard du robot"

    current_pose = np.asarray(mini.get_current_head_pose(), dtype=float)
    head_position = current_pose[:3, 3].copy()

    MOVE_KEYS = {
        "i": (-1, 0, "I: haut"),
        "k": (1, 0, "K: bas"),
        "j": (0, -1, "J: gauche"),
        "l": (0, 1, "L: droite"),
    }
    STEP_KEYS = {
        "+": (1.0, "+: pas augmente"),
        "=": (1.0, "+: pas augmente"),
        "-": (-1.0, "-: pas diminue"),
    }
    QUIT_KEYS = {
        "c": "validation",
        "q": "Q: position par defaut",
    }

    def apply_pose() -> None:
        mini.goto_target(
            head=create_head_pose(
                x=head_position[0],
                y=head_position[1],
                z=head_position[2],
                pitch=pitch,
                yaw=yaw,
                degrees=True,
            ),
            duration=0.3,
        )

    def draw_overlay(frame) -> Any:
        display = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR).copy()
        panel_lines = [
            "ORIENTATION DE LA TETE",
            "I / K : haut / bas",
            "J / L : gauche / droite",
            "+ / - : modifier le pas",
            "C / Entree : valider",
            "Q : continuer sans modifier",
        ]
        panel_height = 12 + len(panel_lines) * 24
        cv2.rectangle(display, (6, 6), (430, panel_height), (0, 0, 0), -1)
        for index, line in enumerate(panel_lines):
            cv2.putText(
                display, line, (14, 28 + index * 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1,
                cv2.LINE_AA,
            )
        cv2.putText(
            display,
            f"pitch={pitch:.0f} yaw={yaw:.0f} pas={step:.0f} | touche: {last_command}",
            (14, panel_height + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
            (0, 255, 0), 2,
        )
        return display

    cv2.namedWindow(window)
    apply_pose()
    print(
        "Orientez la tête du robot pour bien cadrer le plateau : "
        "i/k = haut/bas, j/l = gauche/droite, +/- = pas, "
        "c ou Entrée = valider, q = passer."
    )

    try:
        while True:
            frame = get_frame()
            cv2.imshow(window, draw_overlay(frame))

            key = cv2.waitKey(30) & 0xFF
            if _is_enter_key(key):
                last_command = "validation"
                break
            try:
                key_char = chr(key).lower()
            except ValueError:
                key_char = ""

            if key_char in QUIT_KEYS:
                last_command = QUIT_KEYS[key_char]
                break

            if key_char in MOVE_KEYS:
                dpitch, dyaw, label = MOVE_KEYS[key_char]
                pitch = _clamp(pitch + dpitch * step, GAZE_PITCH_RANGE_DEG)
                yaw = _clamp(yaw + dyaw * step, gaze_yaw_range_deg)
                last_command = label
                apply_pose()
            elif key_char in STEP_KEYS:
                delta, label = STEP_KEYS[key_char]
                step = _clamp(step + delta, GAZE_STEP_RANGE_DEG)
                last_command = label
    finally:
        # Garantit la fermeture de la fenêtre même si get_frame() ou un
        # appel OpenCV lève une exception en cours de boucle.
        cv2.destroyWindow(window)

    return pitch, yaw
