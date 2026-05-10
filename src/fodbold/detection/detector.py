from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from ultralytics import YOLO

from fodbold.config import DetectionConfig


@dataclass(slots=True)
class Detection:
    class_name: str
    confidence: float
    bbox_xyxy: tuple[float, float, float, float]


@dataclass(slots=True)
class FrameDetections:
    ball: Detection | None = None
    players: list[Detection] = field(default_factory=list)
    referees: list[Detection] = field(default_factory=list)
    goalkeepers: list[Detection] = field(default_factory=list)


class FootballDetector:
    CLASS_TO_OUTPUT_FIELD = {
        "ball": "ball",
        "player": "players",
        "referee": "referees",
        "goalkeeper": "goalkeepers",
    }

    def __init__(self, config: DetectionConfig, models_dir: str | Path):
        self.config = config
        self.thresholds = {
            class_name.strip().lower(): threshold
            for class_name, threshold in config.confidence_threshold.items()
        }

        self._validate_thresholds()

        model_path = Path(models_dir) / config.model_file
        if not model_path.exists():
            raise FileNotFoundError(
                f"YOLO model not found: {model_path}. "
                "Place your trained .pt file in paths.models_dir or update detection.model_file."
            )

        self.model = YOLO(str(model_path))

    def detect(self, frame: np.ndarray) -> FrameDetections:
        results = self.model.predict(
            frame,
            imgsz=self.config.image_size,
            device=self.config.device,
            # Note: use the lowest class threshold here so YOLO does not discard
            # low-threshold classes like ball before our per-class filtering runs.
            conf=min(self.thresholds.values()),
            verbose=False,
        )

        detections = FrameDetections()
        ball_candidates: list[Detection] = []

        for result in results:
            for box in result.boxes:
                detection = self._box_to_detection(result, box)
                if detection is None:
                    continue

                if detection.class_name == "ball":
                    ball_candidates.append(detection)
                elif detection.class_name == "player":
                    detections.players.append(detection)
                elif detection.class_name == "referee":
                    detections.referees.append(detection)
                elif detection.class_name == "goalkeeper":
                    detections.goalkeepers.append(detection)

        detections.ball = max(
            ball_candidates,
            key=lambda detection: detection.confidence,
            default=None,
        )

        return detections

    def _box_to_detection(self, result: Any, box: Any) -> Detection | None:
        class_id = int(box.cls.item())
        raw_class_name = result.names.get(class_id, str(class_id))
        class_name = raw_class_name.strip().lower()

        # Note: ignore unexpected model classes defensively instead of crashing.
        if class_name not in self.CLASS_TO_OUTPUT_FIELD:
            return None

        confidence = float(box.conf.item())
        if confidence < self.thresholds[class_name]:
            return None

        x1, y1, x2, y2 = (float(value) for value in box.xyxy.squeeze().tolist())
        return Detection(
            class_name=class_name,
            confidence=confidence,
            bbox_xyxy=(x1, y1, x2, y2),
        )

    def _validate_thresholds(self) -> None:
        missing_classes = set(self.CLASS_TO_OUTPUT_FIELD) - set(self.thresholds)
        if missing_classes:
            missing = ", ".join(sorted(missing_classes))
            raise ValueError(f"Missing confidence thresholds for: {missing}")
