from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np

from fodbold.config import Config
from fodbold.detection.detector import FootballDetector, FrameDetections
from fodbold.team.team_assignment import TeamAssignment
from fodbold.team.team_classifier import TeamClassifier


@dataclass(slots=True)
class PipelineFrameResult:
    frame_index: int
    detections: FrameDetections
    team_classifier_fitted: bool


class FootballPipeline:
    """Runs the current video pipeline: detection, then optional team assignment."""

    def __init__(self, config: Config, project_root: str | Path = "."):
        self.config = config
        self.project_root = Path(project_root)

        self.detector = FootballDetector(
            config=config.detection,
            models_dir=self._resolve_project_path(config.paths["models_dir"]),
        )
        self.team_assignment = self._build_team_assignment()

    def process_frame(self, frame: np.ndarray) -> FrameDetections:
        detections = self.detector.detect(frame)

        if self.team_assignment is not None:
            # Note: team assignment runs after detection and before tracking.
            # During warmup, players keep team=None while jersey colors are collected.
            self.team_assignment.process_frame(frame, detections)

        return detections

    def process_video(
        self,
        video_path: str | Path,
        max_frames: int | None = None,
        frame_stride: int = 1,
    ) -> Iterator[PipelineFrameResult]:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise OSError(f"Could not open video: {video_path}")

        frame_index = 0
        processed_frames = 0

        try:
            while max_frames is None or processed_frames < max_frames:
                ok, frame = cap.read()
                if not ok:
                    break

                if frame_index % frame_stride != 0:
                    frame_index += 1
                    continue

                detections = self.process_frame(frame)
                yield PipelineFrameResult(
                    frame_index=frame_index,
                    detections=detections,
                    team_classifier_fitted=self.team_classifier_is_fitted,
                )

                processed_frames += 1
                frame_index += 1
        finally:
            cap.release()

    @property
    def team_classifier_is_fitted(self) -> bool:
        return self.team_assignment is not None and self.team_assignment.is_fitted

    def _build_team_assignment(self) -> TeamAssignment | None:
        if not self.config.team_classification.enabled:
            return None

        return TeamAssignment(
            classifier=TeamClassifier(
                min_fit_samples=self.config.team_classification.min_fit_samples,
            ),
            jersey_config=self.config.team_classification.to_jersey_color_config(),
            fit_frames=self.config.team_classification.fit_frames,
        )

    def _resolve_project_path(self, path: str) -> Path:
        resolved_path = Path(path)
        if resolved_path.is_absolute():
            return resolved_path

        return self.project_root / resolved_path
