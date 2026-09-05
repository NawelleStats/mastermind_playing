"""Gestes expressifs de Reachy Mini : tête et antennes.

Construits directement sur `goto_target`/`create_head_pose` (API stable et
documentée) plutôt que sur `play_emotion`/`play_dance`, qui dépendent de
bibliothèques d'assets externes (Hugging Face) pas forcément disponibles
hors ligne. Ce module reste donc utilisable sans dépendance réseau.
"""

import time

import numpy as np

try:
    from reachy_mini.utils import create_head_pose
except ImportError:  # permet de développer/tester sans le SDK installé
    create_head_pose = None


def nod_yes(mini, repetitions: int = 2) -> None:
    """Hoche la tête de haut en bas : confirmation, bon essai, victoire."""
    for _ in range(repetitions):
        mini.goto_target(head=create_head_pose(pitch=15, degrees=True), duration=0.35)
        mini.goto_target(head=create_head_pose(pitch=-8, degrees=True), duration=0.35)
    mini.goto_target(head=create_head_pose(), duration=0.3)


def shake_no(mini, repetitions: int = 2) -> None:
    """Secoue la tête de gauche à droite : mauvais essai, défaite."""
    for _ in range(repetitions):
        mini.goto_target(head=create_head_pose(yaw=20, degrees=True), duration=0.3)
        mini.goto_target(head=create_head_pose(yaw=-20, degrees=True), duration=0.3)
    mini.goto_target(head=create_head_pose(), duration=0.3)


def express_joy(mini) -> None:
    """Victoire : tête relevée, antennes dressées et frétillantes."""
    mini.goto_target(
        head=create_head_pose(pitch=-10, degrees=True),
        antennas=np.deg2rad([60, 60]),
        duration=0.5,
    )
    for _ in range(3):
        mini.goto_target(antennas=np.deg2rad([40, 80]), duration=0.2)
        mini.goto_target(antennas=np.deg2rad([80, 40]), duration=0.2)
    mini.goto_target(head=create_head_pose(), antennas=np.deg2rad([0, 0]), duration=0.6)


def express_disappointment(mini) -> None:
    """Défaite : tête basse, antennes tombantes."""
    mini.goto_target(
        head=create_head_pose(pitch=25, degrees=True),
        antennas=np.deg2rad([-30, -30]),
        duration=1.0,
    )
    time.sleep(1.5)
    mini.goto_target(head=create_head_pose(), antennas=np.deg2rad([0, 0]), duration=0.8)


def thinking(mini) -> None:
    """Pose de réflexion : tête légèrement inclinée, pendant que le solveur
    calcule le prochain essai (mode codebreaker)."""
    mini.goto_target(
        head=create_head_pose(roll=12, pitch=5, degrees=True),
        antennas=np.deg2rad([15, -15]),
        duration=0.6,
    )


def wiggle_antennas(mini, repetitions: int = 2) -> None:
    """Petit mouvement d'antennes neutre : accuse réception d'un essai
    sans juger s'il est bon ou mauvais (mode codemaker, avant le score)."""
    for _ in range(repetitions):
        mini.goto_target(antennas=np.deg2rad([25, -25]), duration=0.25)
        mini.goto_target(antennas=np.deg2rad([-25, 25]), duration=0.25)
    mini.goto_target(antennas=np.deg2rad([0, 0]), duration=0.3)
