from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from fodbold.config import Config
from fodbold.detection.detector import FootballDetector, FrameDetections
from fodbold.team.team_assignment import TeamAssignment
from fodbold.team.team_classifier import TeamClassifier
from fodbold.tracking.tracker import (
    build_tracking_artifact,
    default_tracking_artifact_path,
    save_tracking_artifact,
)


@dataclass(slots=True)
class PipelineFrameResult:
    frame_index: int
    detections: FrameDetections
    team_classifier_fitted: bool


def run_tracking_stage(
    *,
    io_artifact_path: str | Path,
    config: Config,
    project_root: str | Path = ".",
    output_path: str | Path | None = None,
) -> Path:
    project_root = Path(project_root)
    model_path = _resolve_project_path(
        Path(config.paths["models_dir"]) / config.detection.model_file,
        project_root,
    )
    interim_dir = _resolve_project_path(config.paths["interim_dir"], project_root)
    tracker_name = config.tracking.algorithm.strip().lower()
    tracker_config = f"{tracker_name}.yaml"

    artifact = build_tracking_artifact(
        io_artifact_path=io_artifact_path,
        model_path=model_path,
        tracker_name=tracker_name,
        tracker_config=tracker_config,
        device=config.detection.device,
        image_size=config.detection.image_size,
        confidence_thresholds=config.detection.confidence_threshold,
    )

    resolved_output_path = Path(output_path) if output_path else default_tracking_artifact_path(
        artifact["video_id"],
        interim_dir,
    )
    save_tracking_artifact(artifact, resolved_output_path)
    return resolved_output_path


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


def _resolve_project_path(path: str | Path, project_root: Path) -> Path:
    resolved_path = Path(path)
    if resolved_path.is_absolute():
        return resolved_path

    return project_root / resolved_path
