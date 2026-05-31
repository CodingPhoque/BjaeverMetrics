from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from ultralytics import YOLO

from fodbold.io.metadata import validate_io_artifact

TRACKING_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "interim_schemas"
    / "schemas"
    / "detection_tracking_artifact.schema.json"
)

# Can maybe be deleted
CLASS_NAME_ALIASES = {
    "keeper": "goalkeeper",
    "goal keeper": "goalkeeper",
}

ALLOWED_CLASS_NAMES = {"player", "goalkeeper", "ball", "referee"}


def build_tracking_artifact(
    *,
    io_artifact_path: str | Path,
    model_path: str | Path,
    tracker_name: str,
    tracker_config: str,
    device: str,
    image_size: int,
    confidence_thresholds: dict[str, float],
) -> dict[str, Any]:
    io_artifact_path = Path(io_artifact_path)
    model_path = Path(model_path)

    if not model_path.exists():
        raise FileNotFoundError(f"YOLO model not found: {model_path}")

    io_artifact = load_io_artifact(io_artifact_path)
    video_path = Path(io_artifact["video"]["path"])
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    fps_original = io_artifact["video_properties"]["fps_original"]
    frame_stride = io_artifact["processing"]["frame_stride"]
    normalized_thresholds = _normalize_thresholds(confidence_thresholds)
    model = YOLO(str(model_path))
    frames = _track_video_frames(
        model=model,
        video_path=video_path,
        segments=io_artifact["processing"]["segments"],
        frame_stride=frame_stride,
        tracker_config=tracker_config,
        device=device,
        image_size=image_size,
        confidence_thresholds=normalized_thresholds,
    )

    if not frames:
        raise ValueError("Tracking artifact must contain at least one processed frame.")

    return {
        "artifact_type": "tracking",
        "schema_version": "1.0",
        "source_io_artifact": _to_artifact_path(io_artifact_path),
        "video_id": io_artifact["video"]["video_id"],
        "model": {
            "name": model_path.stem,
            "weights_path": _to_artifact_path(model_path),
            "classes": _model_classes(model),
        },
        "tracker": {
            "name": tracker_name,
            "config": tracker_config,
        },
        "processing": {
            "fps_processed": fps_original / frame_stride,
            "frame_stride": frame_stride,
        },
        "summary": build_tracking_summary(frames),
        "frames": frames,
    }


def load_io_artifact(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    validate_io_artifact(artifact)
    return artifact


def save_tracking_artifact(artifact: dict[str, Any], output_path: str | Path) -> None:
    validate_tracking_artifact(artifact)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(artifact, file, indent=2, ensure_ascii=False)


def validate_tracking_artifact(
    artifact: dict[str, Any],
    schema_path: str | Path = TRACKING_SCHEMA_PATH,
) -> None:
    schema_path = Path(schema_path)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    try:
        validator.validate(artifact)
    except ValidationError as error:
        raise ValueError(f"Tracking artifact does not match schema: {error.message}") from error


def default_tracking_artifact_path(
    video_id: str,
    interim_dir: str | Path = "data/interim",
) -> Path:
    return Path(interim_dir) / f"{video_id}_tracking.json"


def build_tracking_summary(frames: list[dict[str, Any]]) -> dict[str, Any]:
    objects_by_class: Counter[str] = Counter()

    for frame in frames:
        for tracked_object in frame["objects"]:
            objects_by_class[tracked_object["class_name"]] += 1

    return {
        "frames_processed": len(frames),
        "total_objects": sum(objects_by_class.values()),
        "objects_by_class": dict(objects_by_class),
    }


def extract_tracked_objects(
    result: Any,
    confidence_thresholds: dict[str, float],
) -> list[dict[str, Any]]:
    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        return []

    bbox_values = boxes.xyxy.cpu().tolist()
    class_ids = boxes.cls.int().cpu().tolist()
    confidences = boxes.conf.cpu().tolist()
    track_ids = _extract_track_ids(boxes, len(bbox_values))

    objects = []
    for bbox_xyxy, class_id, confidence, track_id in zip(
        bbox_values,
        class_ids,
        confidences,
        track_ids,
        strict=True,
    ):
        class_name = _normalize_class_name(result.names.get(class_id, str(class_id)))
        if class_name not in ALLOWED_CLASS_NAMES:
            continue

        if confidence < confidence_thresholds[class_name]:
            continue

        objects.append(
            {
                "track_id": track_id,
                "class_id": int(class_id),
                "class_name": class_name,
                "confidence": float(confidence),
                "bbox_xyxy": [float(value) for value in bbox_xyxy],
            }
        )

    return objects


def iter_segment_frames(
    video_path: str | Path,
    segments: list[dict[str, Any]],
    frame_stride: int,
) -> Iterator[tuple[int, Any]]:
    import cv2

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise OSError(f"Could not open video: {video_path}")

    try:
        for segment in segments:
            start_frame = segment["start_frame_inclusive"]
            end_frame = segment["end_frame_exclusive"]
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

            frame_index = start_frame
            while frame_index < end_frame:
                ok, frame = cap.read()
                if not ok:
                    break

                if (frame_index - start_frame) % frame_stride == 0:
                    yield frame_index, frame

                frame_index += 1
    finally:
        cap.release()


def _track_video_frames(
    *,
    model: Any,
    video_path: Path,
    segments: list[dict[str, Any]],
    frame_stride: int,
    tracker_config: str,
    device: str,
    image_size: int,
    confidence_thresholds: dict[str, float],
) -> list[dict[str, Any]]:
    frames = []
    minimum_confidence = min(confidence_thresholds.values())
    current_segment_index = -1

    for frame_index, frame in iter_segment_frames(video_path, segments, frame_stride):
        segment_index = _segment_index_for_frame(frame_index, segments)
        if segment_index != current_segment_index:
            _reset_model_trackers(model)
            current_segment_index = segment_index

        result = model.track(
            frame,
            persist=True,
            tracker=tracker_config,
            conf=minimum_confidence,
            imgsz=image_size,
            device=device,
            verbose=False,
        )[0]

        frames.append(
            {
                "frame_index": frame_index,
                "objects": extract_tracked_objects(result, confidence_thresholds),
            }
        )

    return frames


def _extract_track_ids(boxes: Any, box_count: int) -> list[int | None]:
    if not getattr(boxes, "is_track", False) or boxes.id is None:
        return [None] * box_count

    return [int(track_id) for track_id in boxes.id.int().cpu().tolist()]


def _model_classes(model: Any) -> dict[str, str]:
    return {
        str(class_id): _normalize_class_name(class_name)
        for class_id, class_name in model.names.items()
    }


def _normalize_thresholds(thresholds: dict[str, float]) -> dict[str, float]:
    # Can maybe delete 'normalized' if CLASS_NAME_ALIASES is removed
    normalized = {
        _normalize_class_name(class_name): float(threshold)
        for class_name, threshold in thresholds.items()
    }
    missing_classes = ALLOWED_CLASS_NAMES - set(normalized)
    if missing_classes:
        missing = ", ".join(sorted(missing_classes))
        raise ValueError(f"Missing confidence thresholds for: {missing}")

    return normalized

# Can maybe be deleted if CLASS_NAME_ALIASES is removed
def _normalize_class_name(class_name: Any) -> str:
    normalized = str(class_name).strip().lower()
    return CLASS_NAME_ALIASES.get(normalized, normalized)


def _segment_index_for_frame(frame_index: int, segments: list[dict[str, Any]]) -> int:
    for index, segment in enumerate(segments):
        if segment["start_frame_inclusive"] <= frame_index < segment["end_frame_exclusive"]:
            return index

    raise ValueError(f"Frame {frame_index} is not inside any IO segment.")


def _reset_model_trackers(model: Any) -> None:
    predictor = getattr(model, "predictor", None)
    trackers = getattr(predictor, "trackers", None)
    if not trackers:
        return

    for tracker in trackers:
        tracker.reset()


def _to_artifact_path(path: Path) -> str:
    return str(path).replace("\\", "/")
