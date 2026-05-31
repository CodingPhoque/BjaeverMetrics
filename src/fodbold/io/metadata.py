from __future__ import annotations

import json
import re
from datetime import date as Date
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

IO_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "interim_schemas"
    / "schemas"
    / "io_artifact.schema.json"
)


def get_video_metadata(path: str | Path) -> dict[str, Any]:
    import cv2

    video_path = Path(path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise OSError(f"Could not open video: {video_path}")

    # try-finally block ensures that cap.release() is called if an error occurs while reading properties
    try:
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps_original = float(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        codec_fourcc = _read_codec_fourcc(cap, cv2)
    finally:
        cap.release()

    if frame_count < 1:
        raise ValueError(f"Video must contain at least 1 frame, got {frame_count}")
    if fps_original <= 0:
        raise ValueError(f"Video FPS must be greater than 0, got {fps_original}")
    if width < 1 or height < 1:
        raise ValueError(f"Video dimensions must be positive, got {width}x{height}")

    return {
        "fps_original": fps_original,
        "frame_count": frame_count,
        "duration_seconds": frame_count / fps_original,
        "width": width,
        "height": height,
        "codec_fourcc": codec_fourcc,
        "file_size_bytes": video_path.stat().st_size,
    }


# "*" means that all parameters must be named e.g. video_path=match.mp4, not just match.mp4 as a positional argument
def build_io_artifact(
    *,
    video_path: str | Path,
    date: str,
    home_team: str,
    away_team: str,
    half1_start_seconds: float,
    half1_end_seconds: float,
    half2_start_seconds: float,
    half2_end_seconds: float,
    fps_target: float = 30.0,
    venue: str | None = None,
    video_id: str | None = None,
) -> dict[str, Any]:
    video_path = Path(video_path)
    _validate_iso_date(date)

    video_metadata = get_video_metadata(video_path)
    fps_original = video_metadata["fps_original"]
    duration_seconds = video_metadata["duration_seconds"]

    # Checks if the half time stamps are in the correct order chronologically and don't exceed duration_seconds
    _validate_match_segments(
        half1_start_seconds=half1_start_seconds,
        half1_end_seconds=half1_end_seconds,
        half2_start_seconds=half2_start_seconds,
        half2_end_seconds=half2_end_seconds,
        duration_seconds=duration_seconds,
    )

    if fps_target <= 0:
        raise ValueError(f"fps_target must be greater than 0, got {fps_target}")
    if fps_original <= 0:
        raise ValueError(f"fps_original must be greater than 0, got {fps_original}")

    resolved_video_id = video_id or build_video_id(date, home_team, away_team)

    return {
        "artifact_type": "io",
        "schema_version": "1.0",
        "video": {
            "video_id": resolved_video_id,
            "file_name": video_path.name,
            "path": _to_artifact_path(video_path),
            "file_size_bytes": video_metadata["file_size_bytes"],
        },
        "video_properties": {
            "fps_original": fps_original,
            "frame_count": video_metadata["frame_count"],
            "duration_seconds": video_metadata["duration_seconds"],
            "width": video_metadata["width"],
            "height": video_metadata["height"],
            "codec_fourcc": video_metadata["codec_fourcc"],
        },
        "processing": {
            "fps_target": float(fps_target),
            "frame_stride": max(1, int(round(fps_original / fps_target))),
            "segments": [
                _build_segment(
                    name="first_half",
                    start_seconds=half1_start_seconds,
                    end_seconds=half1_end_seconds,
                    fps_original=fps_original,
                ),
                _build_segment(
                    name="second_half",
                    start_seconds=half2_start_seconds,
                    end_seconds=half2_end_seconds,
                    fps_original=fps_original,
                ),
            ],
        },
        "match": {
            "date": date,
            "home_team": home_team,
            "away_team": away_team,
            "venue": venue,
        },
    }


def save_io_artifact(artifact: dict[str, Any], output_path: str | Path) -> None:
    validate_io_artifact(artifact)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(artifact, file, indent=2, ensure_ascii=False)


def validate_io_artifact(
    artifact: dict[str, Any],
    schema_path: str | Path = IO_SCHEMA_PATH,
) -> None:
    schema_path = Path(schema_path)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    try:
        validator.validate(artifact)
    except ValidationError as error:
        raise ValueError(f"IO artifact does not match schema: {error.message}") from error


def build_video_id(date: str, home_team: str, away_team: str) -> str:
    date_token = date.replace("-", "_")
    return f"{_slugify(home_team)}_vs_{_slugify(away_team)}_{date_token}"


def _build_segment(
    *,
    name: str,
    start_seconds: float,
    end_seconds: float,
    fps_original: float,
) -> dict[str, Any]:
    return {
        "name": name,
        "start_frame_inclusive": _seconds_to_frame(start_seconds, fps_original),
        "end_frame_exclusive": _seconds_to_frame(end_seconds, fps_original),
        "start_time_seconds": float(start_seconds),
        "end_time_seconds": float(end_seconds),
    }


def _seconds_to_frame(seconds: float, fps_original: float) -> int:
    return int(round(seconds * fps_original))


def _validate_match_segments(
    *,
    half1_start_seconds: float,
    half1_end_seconds: float,
    half2_start_seconds: float,
    half2_end_seconds: float,
    duration_seconds: float,
) -> None:
    if not (
        0 <= half1_start_seconds
        < half1_end_seconds
        <= half2_start_seconds
        < half2_end_seconds
    ):
        raise ValueError(
            "Half timestamps must be ordered: "
            "0 <= half1_start < half1_end <= half2_start < half2_end"
        )

    if half2_end_seconds > duration_seconds:
        raise ValueError(
            f"half2_end ({half2_end_seconds:.2f}s) exceeds video duration "
            f"({duration_seconds:.2f}s)"
        )


def _validate_iso_date(value: str) -> None:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"date must use YYYY-MM-DD format, got {value!r}")

    try:
        Date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"date must be a real calendar date, got {value!r}") from error


def _read_codec_fourcc(cap: Any, cv2_module: Any) -> str | None:
    fourcc_int = int(cap.get(cv2_module.CAP_PROP_FOURCC))
    if fourcc_int <= 0:
        return None

    codec = "".join(chr((fourcc_int >> (8 * index)) & 0xFF) for index in range(4))
    if len(codec) != 4 or not codec.strip("\x00"):
        return None
    if not all(char.isprintable() for char in codec):
        return None

    return codec


def _to_artifact_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def _slugify(value: str) -> str:
    slug = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug or "unknown"
