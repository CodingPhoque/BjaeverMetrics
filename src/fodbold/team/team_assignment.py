from __future__ import annotations

import numpy as np

from fodbold.detection.detector import FrameDetections
from fodbold.team.color_features import JerseyColorConfig, extract_jersey_color
from fodbold.team.team_classifier import TeamClassifier


class TeamAssignment:
    """Collects jersey colors during warmup, then assigns team labels to players."""

    def __init__(
        self,
        classifier: TeamClassifier,
        jersey_config: JerseyColorConfig,
        fit_frames: int,
    ):
        self.classifier = classifier
        self.jersey_config = jersey_config
        self.fit_frames = fit_frames
        self.frames_seen = 0
        self.features: list[np.ndarray] = []

    @property
    def is_fitted(self) -> bool:
        return self.classifier.is_fitted

    def process_frame(self, frame: np.ndarray, detections: FrameDetections) -> None:
        if not self.classifier.is_fitted:
            # Note: simple first version. Warmup frames are used to learn team colors,
            # so players in these frames keep team=None and do not get backfilled.
            self._collect_features(frame, detections)
            self.frames_seen += 1

            if self.frames_seen >= self.fit_frames:
                self._fit_if_ready()

            return

        self._assign_teams(frame, detections)

    def _collect_features(self, frame: np.ndarray, detections: FrameDetections) -> None:
        for player in detections.players:
            feature = extract_jersey_color(frame, player.bbox_xyxy, self.jersey_config)
            if feature is not None:
                self.features.append(feature)

    def _fit_if_ready(self) -> None:
        if len(self.features) < self.classifier.min_fit_samples:
            return

        self.classifier.fit(np.array(self.features, dtype=np.float32))

    def _assign_teams(self, frame: np.ndarray, detections: FrameDetections) -> None:
        for player in detections.players:
            feature = extract_jersey_color(frame, player.bbox_xyxy, self.jersey_config)
            if feature is not None:
                player.team = self.classifier.predict(feature)
