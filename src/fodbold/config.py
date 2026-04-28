from dataclasses import dataclass, field
from pathlib import Path
import yaml

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
    test_mode_second: int

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
            tracking=TrackingConfig(**raw["tracking"]),
            debug=DebugConfig(**raw["debug"]),
            paths=raw["paths"],
            output=raw["output"],
            logging=raw["logging"]
        )
