import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fodbold.detection.detector import Detection, FrameDetections  # noqa: E402
from fodbold.pipeline import FootballPipeline  # noqa: E402
from fodbold.team.color_features import JerseyColorConfig  # noqa: E402
from fodbold.team.team_assignment import TeamAssignment  # noqa: E402
from fodbold.team.team_classifier import TeamClassifier  # noqa: E402


def test_pipeline_runs_detection_then_team_assignment():
    pipeline = FootballPipeline.__new__(FootballPipeline)
    pipeline.detector = FakeDetector()
    pipeline.team_assignment = TeamAssignment(
        classifier=TeamClassifier(min_fit_samples=2, random_state=0),
        jersey_config=JerseyColorConfig(),
        fit_frames=1,
    )

    frame = _two_player_frame()
    pipeline.process_frame(frame)
    detections = pipeline.process_frame(frame)

    assert detections.players[0].team in {"team_a", "team_b"}
    assert detections.players[1].team in {"team_a", "team_b"}
    assert detections.players[0].team != detections.players[1].team


def test_pipeline_can_run_without_team_assignment():
    pipeline = FootballPipeline.__new__(FootballPipeline)
    pipeline.detector = FakeDetector()
    pipeline.team_assignment = None

    detections = pipeline.process_frame(_two_player_frame())

    assert detections.players[0].team is None
    assert detections.players[1].team is None


class FakeDetector:
    def detect(self, frame):
        return FrameDetections(
            players=[
                Detection("player", 0.90, (0, 0, 60, 100)),
                Detection("player", 0.91, (70, 0, 130, 100)),
            ]
        )


def _two_player_frame() -> np.ndarray:
    frame = np.full((100, 140, 3), (0, 128, 0), dtype=np.uint8)
    frame[20:65, 12:48] = (255, 0, 0)
    frame[20:65, 82:118] = (0, 140, 255)
    return frame
