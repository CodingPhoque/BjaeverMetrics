from dataclasses import dataclass
from pathlib import Path

import yaml

from fodbold.team.color_features import JerseyColorConfig

# TODO why only these dataclasses? Why not paths, or output, or logging?

@dataclass
class DetectionConfig:
    model_file: str
    device: str
    image_size: int
    confidence_threshold: dict[str, float]

@dataclass
class TrackingConfig:
    algorithm: str
    track_buffer: int
    match_threshold: float # TODO What is it?

@dataclass
class VideoConfig:
    fps_target: int
    test_mode_seconds: int

@dataclass
class TeamClassificationConfig:
    enabled: bool
    fit_frames: int
    min_fit_samples: int
    color_space: str
    jersey_crop: dict[str, float]
    grass_filter: dict

    def to_jersey_color_config(self) -> JerseyColorConfig:
        # Note: this keeps YAML tuning values in one place while color extraction
        # receives the small config object it actually needs.
        return JerseyColorConfig(
            x_margin_ratio=self.jersey_crop["x_margin_ratio"],
            y_start_ratio=self.jersey_crop["y_start_ratio"],
            y_end_ratio=self.jersey_crop["y_end_ratio"],
            min_pixels=self.grass_filter["min_pixels"],
            grass_hsv_lower=tuple(self.grass_filter["hsv_lower"]),
            grass_hsv_upper=tuple(self.grass_filter["hsv_upper"]),
        )

@dataclass
class DebugConfig:
    save_detection_video: bool
    save_tracking_video: bool
    save_final_video: bool
    output_dir: str

@dataclass # TODO What is it?
class Config:
    video: VideoConfig
    detection: DetectionConfig
    team_classification: TeamClassificationConfig
    tracking: TrackingConfig
    debug: DebugConfig
    paths: dict[str, str] 
    output: dict
    logging: dict

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        with open(path, "r") as f:
            raw = yaml.safe_load(f)
        return cls(
            video=VideoConfig(**raw["video"]),
            detection=DetectionConfig(**raw["detection"]),
            team_classification=TeamClassificationConfig(**raw["team_classification"]),
            tracking=TrackingConfig(**raw["tracking"]),
            debug=DebugConfig(**raw["debug"]),
            paths=raw["paths"],
            output=raw["output"],
            logging=raw["logging"]
        )
