import os
import time

import pytest
from reachy_mini import ReachyMini
from config import REACHY_MINI_HOST, REACHY_MINI_PORT, REACHY_MINI_CONNECTION_MODE, REACHY_MINI_MEDIA_BACKEND


def test_speaker_plays_builtin_sound():
    if os.environ.get("RUN_REACHY_HARDWARE_TESTS") != "1":
        pytest.skip("Set RUN_REACHY_HARDWARE_TESTS=1 to test Reachy Mini audio")

    with ReachyMini(
        host=REACHY_MINI_HOST,
        port=REACHY_MINI_PORT,
        connection_mode=REACHY_MINI_CONNECTION_MODE,
        spawn_daemon=False,
        media_backend=REACHY_MINI_MEDIA_BACKEND,
    ) as mini:
        print("Test du haut-parleur...")
        mini.media.play_sound("wake_up.wav")
        time.sleep(1.5)
        print("Test terminé.")
