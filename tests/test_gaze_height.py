import sys

import numpy as np

from perception.peg_localizer import BoardLayout
from robotics import reachy_client


def test_height_keys_raise_and_lower_head(monkeypatch):
    class FakeCV2:
        COLOR_RGB2BGR = 0
        FONT_HERSHEY_SIMPLEX = 0
        LINE_AA = 0

        def __init__(self):
            self.keys = iter((ord("r"), ord("f"), ord("c")))

        @staticmethod
        def cvtColor(frame, code):
            return frame.copy()

        @staticmethod
        def rectangle(*args, **kwargs):
            pass

        @staticmethod
        def putText(*args, **kwargs):
            pass

        @staticmethod
        def namedWindow(*args, **kwargs):
            pass

        @staticmethod
        def imshow(*args, **kwargs):
            pass

        def waitKey(self, delay):
            return next(self.keys)

        @staticmethod
        def destroyWindow(*args, **kwargs):
            pass

    class FakeMini:
        def __init__(self):
            self.targets = []

        @staticmethod
        def get_current_body_yaw():
            return 0.0

        @staticmethod
        def get_current_head_pose():
            pose = np.eye(4)
            pose[2, 3] = 0.3
            return pose

        def goto_target(self, head, duration, **kwargs):
            self.targets.append((head[2, 3], duration, kwargs.get("body_yaw")))

    monkeypatch.setitem(sys.modules, "cv2", FakeCV2())
    mini = FakeMini()

    gaze = reachy_client.adjust_gaze_interactively(
        mini, lambda: np.zeros((2, 2, 3), dtype=np.uint8)
    )

    assert gaze == (0.0, 0.0, 0.3)
    assert mini.targets == [
        (0.3, 0.8, None),
        (0.31, 0.8, None),
        (0.3, 0.8, None),
    ]


def test_layout_round_trips_calibrated_height(tmp_path):
    layout = BoardLayout(
        rows=[[(10, 20)]],
        gaze={"pitch_deg": 24.0, "yaw_deg": -8.0, "height_m": 0.37},
    )
    calibration_path = tmp_path / "calibration.json"

    layout.save(str(calibration_path))

    assert BoardLayout.load(str(calibration_path)).gaze == layout.gaze
