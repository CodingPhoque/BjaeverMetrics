from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from fodbold.io.metadata import validate_io_artifact
from fodbold.team.team_assignment import validate_team_assignment_artifact
from fodbold.tracking.tracker import validate_tracking_artifact

STATS_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "interim_schemas"
    / "schemas"
    / "stats_artifact.schema.json"
)

UNKNOWN_TEAM = "unknown"


def build_stats_artifact(
    *,
    io_artifact_path: str | Path,
    tracking_artifact_path: str | Path,
    team_assignment_artifact_path: str | Path,
    goals_home: int,
    goals_away: int,
    shots_on_target_home: int,
    shots_on_target_away: int,
    max_possession_distance_ratio: float,
    min_possession_confirm_seconds: float,
    max_ball_missing_seconds: float,
    use_ball_kalman_filter: bool,
    max_ball_interpolation_seconds: float,
    min_pass_control_seconds: float,
    max_pass_gap_seconds: float,
    min_turnover_control_seconds: float,
    max_turnover_gap_seconds: float,
) -> dict[str, Any]:
    _validate_manual_count("goals_home", goals_home)
    _validate_manual_count("goals_away", goals_away)
    _validate_manual_count("shots_on_target_home", shots_on_target_home)
    _validate_manual_count("shots_on_target_away", shots_on_target_away)

    io_artifact_path = Path(io_artifact_path)
    tracking_artifact_path = Path(tracking_artifact_path)
    team_assignment_artifact_path = Path(team_assignment_artifact_path)

    io_artifact = load_io_artifact(io_artifact_path)
    tracking_artifact = load_tracking_artifact(tracking_artifact_path)
    team_assignment_artifact = load_team_assignment_artifact(team_assignment_artifact_path)

    track_team_lookup = build_track_team_lookup(team_assignment_artifact)
    fps_processed = tracking_artifact["processing"]["fps_processed"]
    possession_timeline = build_possession_timeline(
        tracking_artifact=tracking_artifact,
        track_team_lookup=track_team_lookup,
        fps_processed=fps_processed,
        max_possession_distance_ratio=max_possession_distance_ratio,
        min_possession_confirm_seconds=min_possession_confirm_seconds,
        max_ball_missing_seconds=max_ball_missing_seconds,
        use_ball_kalman_filter=use_ball_kalman_filter,
        max_ball_interpolation_seconds=max_ball_interpolation_seconds,
    )
    possession_intervals = build_possession_intervals(possession_timeline)

    passes = count_passes(
        intervals=possession_intervals,
        fps_processed=fps_processed,
        min_control_seconds=min_pass_control_seconds,
        max_pass_gap_seconds=max_pass_gap_seconds,
        segments=io_artifact["processing"]["segments"],
    )
    turnovers = count_turnovers(
        intervals=possession_intervals,
        fps_processed=fps_processed,
        min_control_seconds=min_turnover_control_seconds,
        max_turnover_gap_seconds=max_turnover_gap_seconds,
        segments=io_artifact["processing"]["segments"],
    )

    return {
        "artifact_type": "stats",
        "schema_version": "1.0",
        "source_io_artifact": _to_artifact_path(io_artifact_path),
        "source_tracking_artifact": _to_artifact_path(tracking_artifact_path),
        "source_team_assignment_artifact": _to_artifact_path(team_assignment_artifact_path),
        "video_id": io_artifact["video"]["video_id"],
        "match": io_artifact["match"],
        "method": {
            "possession": {
                "max_possession_distance_ratio": max_possession_distance_ratio,
                "min_possession_confirm_seconds": min_possession_confirm_seconds,
                "max_ball_missing_seconds": max_ball_missing_seconds,
                "use_ball_kalman_filter": use_ball_kalman_filter,
                "max_ball_interpolation_seconds": max_ball_interpolation_seconds,
            },
            "passes": {
                "min_control_seconds": min_pass_control_seconds,
                "max_pass_gap_seconds": max_pass_gap_seconds,
            },
            "turnovers": {
                "min_control_seconds": min_turnover_control_seconds,
                "max_turnover_gap_seconds": max_turnover_gap_seconds,
            },
        },
        "stats": {
            "possession": build_possession_stat(
                possession_timeline,
                io_artifact["processing"]["segments"],
            ),
            "passes": build_count_stat(passes, io_artifact["processing"]["segments"]),
            "turnovers": build_count_stat(turnovers, io_artifact["processing"]["segments"]),
            "shots_on_target": {
                "source": "manual",
                "unit": "count",
                "home": shots_on_target_home,
                "away": shots_on_target_away,
            },
            "goals": {
                "source": "manual",
                "unit": "count",
                "home": goals_home,
                "away": goals_away,
            },
        },
        "quality": {
            "tracking": tracking_artifact["summary"],
            "team_assignment": team_assignment_artifact["summary"],
            "possession": build_possession_quality(possession_timeline),
        },
    }


def load_io_artifact(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    validate_io_artifact(artifact)
    return artifact


def load_tracking_artifact(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    validate_tracking_artifact(artifact)
    return artifact


def load_team_assignment_artifact(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    validate_team_assignment_artifact(artifact)
    return artifact


def save_stats_artifact(artifact: dict[str, Any], output_path: str | Path) -> None:
    validate_stats_artifact(artifact)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(artifact, file, indent=2, ensure_ascii=False)


def validate_stats_artifact(
    artifact: dict[str, Any],
    schema_path: str | Path = STATS_SCHEMA_PATH,
) -> None:
    schema_path = Path(schema_path)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    try:
        validator.validate(artifact)
    except ValidationError as error:
        raise ValueError(f"Stats artifact does not match schema: {error.message}") from error


def default_stats_artifact_path(
    video_id: str,
    interim_dir: str | Path = "data/interim",
) -> Path:
    return Path(interim_dir) / f"{video_id}_stats.json"


def build_track_team_lookup(team_assignment_artifact: dict[str, Any]) -> dict[int, str]:
    return {
        assigned_track["track_id"]: assigned_track["team"]
        for assigned_track in team_assignment_artifact["assigned_tracks"]
    }


def build_possession_timeline(
    *,
    tracking_artifact: dict[str, Any],
    track_team_lookup: dict[int, str],
    fps_processed: float,
    max_possession_distance_ratio: float,
    min_possession_confirm_seconds: float,
    max_ball_missing_seconds: float,
    use_ball_kalman_filter: bool,
    max_ball_interpolation_seconds: float,
) -> list[dict[str, Any]]:
    min_confirm_frames = _seconds_to_processed_frames(
        min_possession_confirm_seconds,
        fps_processed,
        minimum=1,
    )
    max_missing_frames = _seconds_to_processed_frames(
        max_ball_missing_seconds,
        fps_processed,
        minimum=0,
    )

    ball_timeline = build_ball_timeline(
        tracking_artifact["frames"],
        fps_processed=fps_processed,
        use_ball_kalman_filter=use_ball_kalman_filter,
        max_ball_interpolation_seconds=max_ball_interpolation_seconds,
    )
    raw_timeline = []
    for frame, ball_entry in zip(tracking_artifact["frames"], ball_timeline, strict=True):
        raw_timeline.append(
            _raw_possession_candidate(
                frame,
                ball_entry,
                track_team_lookup,
                max_possession_distance_ratio,
            )
        )

    timeline = []
    last_confirmed: tuple[str, int] | None = None
    pending_candidate: tuple[str, int] | None = None
    pending_count = 0
    missing_count = 0

    for raw_entry in raw_timeline:
        candidate = raw_entry["candidate"]

        if candidate is None:
            pending_candidate = None
            pending_count = 0
            if last_confirmed is not None and missing_count < max_missing_frames:
                team, track_id = last_confirmed
                missing_count += 1
            else:
                team = UNKNOWN_TEAM
                track_id = None
                missing_count += 1
        else:
            missing_count = 0
            if candidate == last_confirmed:
                pending_candidate = None
                pending_count = 0
                team, track_id = candidate
            else:
                if candidate == pending_candidate:
                    pending_count += 1
                else:
                    pending_candidate = candidate
                    pending_count = 1

                if pending_count >= min_confirm_frames:
                    last_confirmed = candidate
                    pending_candidate = None
                    pending_count = 0
                    team, track_id = candidate
                elif last_confirmed is not None:
                    team, track_id = last_confirmed
                else:
                    team = UNKNOWN_TEAM
                    track_id = None

        timeline.append(
            {
                "frame_index": raw_entry["frame_index"],
                "has_ball": raw_entry["has_ball"],
                "has_detected_ball": raw_entry["has_detected_ball"],
                "has_estimated_ball": raw_entry["has_estimated_ball"],
                "team": team,
                "track_id": track_id,
            }
        )

    return timeline


def build_possession_intervals(timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    intervals = []
    current_interval: dict[str, Any] | None = None

    for position, entry in enumerate(timeline):
        state = (entry["team"], entry["track_id"])
        if current_interval is None:
            current_interval = _start_interval(entry, position)
            continue

        current_state = (current_interval["team"], current_interval["track_id"])
        if state == current_state:
            current_interval["end_frame"] = entry["frame_index"]
            current_interval["end_position"] = position
            current_interval["frame_count"] += 1
            continue

        intervals.append(current_interval)
        current_interval = _start_interval(entry, position)

    if current_interval is not None:
        intervals.append(current_interval)

    return intervals


def build_possession_stat(
    timeline: list[dict[str, Any]],
    segments: list[dict[str, Any]],
) -> dict[str, Any]:
    total_counts = _count_timeline_teams(timeline)
    return {
        "source": "computed",
        "unit": "percent",
        **_counts_to_percentages(total_counts),
        "by_segment": [
            {
                "segment_name": segment["name"],
                **_counts_to_percentages(
                    _count_timeline_teams(
                        [
                            entry
                            for entry in timeline
                            if _frame_in_segment(entry["frame_index"], segment)
                        ]
                    )
                ),
            }
            for segment in segments
        ],
    }


def count_passes(
    *,
    intervals: list[dict[str, Any]],
    fps_processed: float,
    min_control_seconds: float,
    max_pass_gap_seconds: float,
    segments: list[dict[str, Any]],
) -> dict[str, Any]:
    min_control_frames = _seconds_to_processed_frames(min_control_seconds, fps_processed, minimum=1)
    max_gap_frames = _seconds_to_processed_frames(max_pass_gap_seconds, fps_processed, minimum=0)
    counts = _empty_count_result(segments)
    controlled_intervals = _controlled_intervals(intervals, min_control_frames)

    for previous_interval, next_interval in zip(
        controlled_intervals,
        controlled_intervals[1:],
        strict=False,
    ):
        gap_frames = next_interval["start_position"] - previous_interval["end_position"] - 1
        if gap_frames > max_gap_frames:
            continue
        if previous_interval["team"] != next_interval["team"]:
            continue
        if previous_interval["track_id"] == next_interval["track_id"]:
            continue

        team = next_interval["team"]
        counts["total"][team] += 1
        segment_name = _segment_name_for_frame(next_interval["start_frame"], segments)
        if segment_name is not None:
            counts["by_segment"][segment_name][team] += 1

    return counts


def count_turnovers(
    *,
    intervals: list[dict[str, Any]],
    fps_processed: float,
    min_control_seconds: float,
    max_turnover_gap_seconds: float,
    segments: list[dict[str, Any]],
) -> dict[str, Any]:
    min_control_frames = _seconds_to_processed_frames(min_control_seconds, fps_processed, minimum=1)
    max_gap_frames = _seconds_to_processed_frames(max_turnover_gap_seconds, fps_processed, minimum=0)
    counts = _empty_count_result(segments)
    controlled_intervals = _controlled_intervals(intervals, min_control_frames)

    for previous_interval, next_interval in zip(
        controlled_intervals,
        controlled_intervals[1:],
        strict=False,
    ):
        gap_frames = next_interval["start_position"] - previous_interval["end_position"] - 1
        if gap_frames > max_gap_frames:
            continue
        if previous_interval["team"] == next_interval["team"]:
            continue

        losing_team = previous_interval["team"]
        counts["total"][losing_team] += 1
        segment_name = _segment_name_for_frame(next_interval["start_frame"], segments)
        if segment_name is not None:
            counts["by_segment"][segment_name][losing_team] += 1

    return counts


def build_count_stat(
    count_result: dict[str, Any],
    segments: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "source": "computed",
        "unit": "count",
        "home": count_result["total"]["home"],
        "away": count_result["total"]["away"],
        "unknown": count_result["total"]["unknown"],
        "by_segment": [
            {
                "segment_name": segment["name"],
                "home": count_result["by_segment"][segment["name"]]["home"],
                "away": count_result["by_segment"][segment["name"]]["away"],
                "unknown": count_result["by_segment"][segment["name"]]["unknown"],
            }
            for segment in segments
        ],
    }


def build_possession_quality(timeline: list[dict[str, Any]]) -> dict[str, int]:
    frames_with_ball = sum(1 for entry in timeline if entry["has_ball"])
    frames_with_detected_ball = sum(1 for entry in timeline if entry["has_detected_ball"])
    frames_with_estimated_ball = sum(1 for entry in timeline if entry["has_estimated_ball"])
    frames_with_possession = sum(1 for entry in timeline if entry["team"] != UNKNOWN_TEAM)
    return {
        "frames_with_ball": frames_with_ball,
        "frames_with_detected_ball": frames_with_detected_ball,
        "frames_with_estimated_ball": frames_with_estimated_ball,
        "frames_with_possession": frames_with_possession,
        "frames_unknown_possession": len(timeline) - frames_with_possession,
    }


def build_ball_timeline(
    frames: list[dict[str, Any]],
    *,
    fps_processed: float,
    use_ball_kalman_filter: bool,
    max_ball_interpolation_seconds: float,
) -> list[dict[str, Any]]:
    max_interpolation_frames = _seconds_to_processed_frames(
        max_ball_interpolation_seconds,
        fps_processed,
        minimum=0,
    )
    kalman: cv2.KalmanFilter | None = None
    missing_frames = 0
    timeline = []

    for frame in frames:
        ball = _best_ball_object(frame["objects"])
        if ball is not None:
            center = _bbox_center(ball["bbox_xyxy"])
            if use_ball_kalman_filter:
                if kalman is None:
                    kalman = _create_ball_kalman_filter(center)
                else:
                    kalman.predict()
                    kalman.correct(_kalman_measurement(center))
            missing_frames = 0
            timeline.append(
                {
                    "frame_index": frame["frame_index"],
                    "has_ball": True,
                    "has_detected_ball": True,
                    "has_estimated_ball": False,
                    "center": center,
                }
            )
            continue

        if (
            use_ball_kalman_filter
            and kalman is not None
            and missing_frames < max_interpolation_frames
        ):
            prediction = kalman.predict()
            missing_frames += 1
            timeline.append(
                {
                    "frame_index": frame["frame_index"],
                    "has_ball": True,
                    "has_detected_ball": False,
                    "has_estimated_ball": True,
                    "center": (float(prediction[0, 0]), float(prediction[1, 0])),
                }
            )
            continue

        missing_frames += 1
        timeline.append(
            {
                "frame_index": frame["frame_index"],
                "has_ball": False,
                "has_detected_ball": False,
                "has_estimated_ball": False,
                "center": None,
            }
        )

    return timeline


def _raw_possession_candidate(
    frame: dict[str, Any],
    ball_entry: dict[str, Any],
    track_team_lookup: dict[int, str],
    max_possession_distance_ratio: float,
) -> dict[str, Any]:
    if not ball_entry["has_ball"]:
        return {
            "frame_index": frame["frame_index"],
            "has_ball": False,
            "has_detected_ball": False,
            "has_estimated_ball": False,
            "candidate": None,
        }

    best_candidate: tuple[str, int] | None = None
    best_distance_ratio = math.inf
    ball_center = ball_entry["center"]

    for tracked_object in frame["objects"]:
        if tracked_object["class_name"] != "player":
            continue
        track_id = tracked_object["track_id"]
        if not isinstance(track_id, int) or track_id not in track_team_lookup:
            continue

        player_bbox = tracked_object["bbox_xyxy"]
        distance_ratio = _distance(ball_center, _bbox_foot_point(player_bbox)) / _bbox_height(
            player_bbox
        )
        if distance_ratio < best_distance_ratio:
            best_distance_ratio = distance_ratio
            best_candidate = (track_team_lookup[track_id], track_id)

    if best_candidate is None or best_distance_ratio > max_possession_distance_ratio:
        return {
            "frame_index": frame["frame_index"],
            "has_ball": True,
            "has_detected_ball": ball_entry["has_detected_ball"],
            "has_estimated_ball": ball_entry["has_estimated_ball"],
            "candidate": None,
        }

    return {
        "frame_index": frame["frame_index"],
        "has_ball": True,
        "has_detected_ball": ball_entry["has_detected_ball"],
        "has_estimated_ball": ball_entry["has_estimated_ball"],
        "candidate": best_candidate,
    }


def _best_ball_object(objects: list[dict[str, Any]]) -> dict[str, Any] | None:
    balls = [tracked_object for tracked_object in objects if tracked_object["class_name"] == "ball"]
    if not balls:
        return None

    return max(balls, key=lambda tracked_object: tracked_object["confidence"])


def _create_ball_kalman_filter(center: tuple[float, float]) -> cv2.KalmanFilter:
    kalman = cv2.KalmanFilter(4, 2)
    kalman.transitionMatrix = np.array(
        [
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ],
        dtype=np.float32,
    )
    kalman.measurementMatrix = np.array(
        [
            [1, 0, 0, 0],
            [0, 1, 0, 0],
        ],
        dtype=np.float32,
    )
    kalman.processNoiseCov = np.eye(4, dtype=np.float32) * 1e-2
    kalman.measurementNoiseCov = np.eye(2, dtype=np.float32) * 1e-1
    kalman.errorCovPost = np.eye(4, dtype=np.float32)
    kalman.statePost = np.array(
        [[center[0]], [center[1]], [0], [0]],
        dtype=np.float32,
    )
    return kalman


def _kalman_measurement(center: tuple[float, float]) -> np.ndarray:
    return np.array([[center[0]], [center[1]]], dtype=np.float32)


def _start_interval(entry: dict[str, Any], position: int) -> dict[str, Any]:
    return {
        "team": entry["team"],
        "track_id": entry["track_id"],
        "start_frame": entry["frame_index"],
        "end_frame": entry["frame_index"],
        "start_position": position,
        "end_position": position,
        "frame_count": 1,
    }


def _controlled_intervals(
    intervals: list[dict[str, Any]],
    min_control_frames: int,
) -> list[dict[str, Any]]:
    return [
        interval
        for interval in intervals
        if interval["team"] != UNKNOWN_TEAM and interval["frame_count"] >= min_control_frames
    ]


def _empty_count_result(segments: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total": {"home": 0, "away": 0, "unknown": 0},
        "by_segment": {
            segment["name"]: {"home": 0, "away": 0, "unknown": 0}
            for segment in segments
        },
    }


def _count_timeline_teams(timeline: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"home": 0, "away": 0, "unknown": 0}
    for entry in timeline:
        team = entry["team"] if entry["team"] in {"home", "away"} else UNKNOWN_TEAM
        counts[team] += 1

    return counts


def _counts_to_percentages(counts: dict[str, int]) -> dict[str, float]:
    total = counts["home"] + counts["away"] + counts["unknown"]
    if total == 0:
        return {"home": 0.0, "away": 0.0, "unknown": 0.0}

    return {
        "home": round((counts["home"] / total) * 100, 1),
        "away": round((counts["away"] / total) * 100, 1),
        "unknown": round((counts["unknown"] / total) * 100, 1),
    }


def _segment_name_for_frame(
    frame_index: int,
    segments: list[dict[str, Any]],
) -> str | None:
    for segment in segments:
        if _frame_in_segment(frame_index, segment):
            return segment["name"]

    return None


def _frame_in_segment(frame_index: int, segment: dict[str, Any]) -> bool:
    return segment["start_frame_inclusive"] <= frame_index < segment["end_frame_exclusive"]


def _seconds_to_processed_frames(seconds: float, fps_processed: float, *, minimum: int) -> int:
    return max(minimum, int(round(seconds * fps_processed)))


def _bbox_center(bbox_xyxy: list[float]) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox_xyxy
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def _bbox_foot_point(bbox_xyxy: list[float]) -> tuple[float, float]:
    x1, _, x2, y2 = bbox_xyxy
    return ((x1 + x2) / 2, y2)


def _bbox_height(bbox_xyxy: list[float]) -> float:
    _, y1, _, y2 = bbox_xyxy
    return max(y2 - y1, 1.0)


def _distance(point_a: tuple[float, float], point_b: tuple[float, float]) -> float:
    return math.dist(point_a, point_b)


def _validate_manual_count(name: str, value: int) -> None:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer.")


def _to_artifact_path(path: Path) -> str:
    return str(path).replace("\\", "/")
