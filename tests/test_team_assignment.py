import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fodbold.detection.detector import Detection, FrameDetections  # noqa: E402
from fodbold.team.color_features import JerseyColorConfig  # noqa: E402
from fodbold.team.team_assignment import TeamAssignment  # noqa: E402
from fodbold.team.team_classifier import TeamClassifier  # noqa: E402


def test_warmup_frame_collects_features_but_does_not_assign_team():
    frame = _two_player_frame()
    detections = _two_player_detections()
    assignment = TeamAssignment(
        classifier=TeamClassifier(min_fit_samples=2, random_state=0),
        jersey_config=JerseyColorConfig(),
        fit_frames=1,
    )

    assignment.process_frame(frame, detections)

    assert assignment.is_fitted
    assert detections.players[0].team is None
    assert detections.players[1].team is None


def test_after_warmup_assigns_team_to_players():
    frame = _two_player_frame()
    assignment = TeamAssignment(
        classifier=TeamClassifier(min_fit_samples=2, random_state=0),
        jersey_config=JerseyColorConfig(),
        fit_frames=1,
    )

    assignment.process_frame(frame, _two_player_detections())
    detections = _two_player_detections()
    assignment.process_frame(frame, detections)

    assert detections.players[0].team in {"team_a", "team_b"}
    assert detections.players[1].team in {"team_a", "team_b"}
    assert detections.players[0].team != detections.players[1].team


def _two_player_frame() -> np.ndarray:
    frame = np.full((100, 140, 3), (0, 128, 0), dtype=np.uint8)
    frame[20:65, 12:48] = (255, 0, 0)
    frame[20:65, 82:118] = (0, 140, 255)
    return frame


def _two_player_detections() -> FrameDetections:
    return FrameDetections(
        players=[
            Detection("player", 0.90, (0, 0, 60, 100)),
            Detection("player", 0.91, (70, 0, 130, 100)),
        ]
    )
