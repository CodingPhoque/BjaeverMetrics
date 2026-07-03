from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fodbold.stats.stats import (  # noqa: E402
    UNKNOWN_TEAM,
    _controlled_intervals,
    _seconds_to_processed_frames,
    _segment_name_for_frame,
    build_possession_intervals,
    build_possession_timeline,
    build_track_team_lookup,
    load_io_artifact,
    load_team_assignment_artifact,
    load_tracking_artifact,
)


DEFAULT_MAX_POSSESSION_DISTANCE_RATIO = 0.55
DEFAULT_MIN_POSSESSION_CONFIRM_SECONDS = 0.30
DEFAULT_MAX_BALL_MISSING_SECONDS = 0.50
DEFAULT_USE_BALL_KALMAN_FILTER = True
DEFAULT_MAX_BALL_INTERPOLATION_SECONDS = 1.00
DEFAULT_MIN_PASS_CONTROL_SECONDS = 0.30
DEFAULT_MAX_PASS_GAP_SECONDS = 2.00


def main() -> None:
    args = parse_args()

    payload = build_system_pass_export(
        io_artifact_path=args.io,
        tracking_artifact_path=args.tracking,
        team_assignment_artifact_path=args.team_assignment,
        team_a_system=args.team_a_system,
        team_d_system=args.team_d_system,
        max_possession_distance_ratio=args.max_possession_distance_ratio,
        min_possession_confirm_seconds=args.min_possession_confirm_seconds,
        max_ball_missing_seconds=args.max_ball_missing_seconds,
        use_ball_kalman_filter=args.use_ball_kalman_filter,
        max_ball_interpolation_seconds=args.max_ball_interpolation_seconds,
        min_pass_control_seconds=args.min_pass_control_seconds,
        max_pass_gap_seconds=args.max_pass_gap_seconds,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(payload['events'])} system pass events to {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract individual system pass events from BjaeverMetrics artifacts.",
    )
    parser.add_argument("--io", required=True, help="Path to *_io.json artifact.")
    parser.add_argument("--tracking", required=True, help="Path to *_tracking.json artifact.")
    parser.add_argument(
        "--team-assignment",
        required=True,
        help="Path to *_team_assignment.json artifact.",
    )
    parser.add_argument("--output", required=True, help="Output JSON path.")
    parser.add_argument(
        "--team-a-system",
        choices=["home", "away"],
        default="home",
        help="Which system team maps to annotator Hold A.",
    )
    parser.add_argument(
        "--team-d-system",
        choices=["home", "away"],
        default="away",
        help="Which system team maps to annotator Hold D.",
    )
    parser.add_argument(
        "--max-possession-distance-ratio",
        type=float,
        default=DEFAULT_MAX_POSSESSION_DISTANCE_RATIO,
    )
    parser.add_argument(
        "--min-possession-confirm-seconds",
        type=float,
        default=DEFAULT_MIN_POSSESSION_CONFIRM_SECONDS,
    )
    parser.add_argument(
        "--max-ball-missing-seconds",
        type=float,
        default=DEFAULT_MAX_BALL_MISSING_SECONDS,
    )
    parser.add_argument(
        "--max-ball-interpolation-seconds",
        type=float,
        default=DEFAULT_MAX_BALL_INTERPOLATION_SECONDS,
    )
    parser.add_argument(
        "--min-pass-control-seconds",
        type=float,
        default=DEFAULT_MIN_PASS_CONTROL_SECONDS,
    )
    parser.add_argument(
        "--max-pass-gap-seconds",
        type=float,
        default=DEFAULT_MAX_PASS_GAP_SECONDS,
    )
    parser.add_argument(
        "--use-ball-kalman-filter",
        action=argparse.BooleanOptionalAction,
        default=DEFAULT_USE_BALL_KALMAN_FILTER,
    )
    return parser.parse_args()


def build_system_pass_export(
    *,
    io_artifact_path: str | Path,
    tracking_artifact_path: str | Path,
    team_assignment_artifact_path: str | Path,
    team_a_system: str,
    team_d_system: str,
    max_possession_distance_ratio: float,
    min_possession_confirm_seconds: float,
    max_ball_missing_seconds: float,
    use_ball_kalman_filter: bool,
    max_ball_interpolation_seconds: float,
    min_pass_control_seconds: float,
    max_pass_gap_seconds: float,
) -> dict[str, Any]:
    io_artifact_path = Path(io_artifact_path)
    tracking_artifact_path = Path(tracking_artifact_path)
    team_assignment_artifact_path = Path(team_assignment_artifact_path)

    io_artifact = load_io_artifact(io_artifact_path)
    tracking_artifact = load_tracking_artifact(tracking_artifact_path)
    team_assignment_artifact = load_team_assignment_artifact(team_assignment_artifact_path)

    track_team_lookup = build_track_team_lookup(team_assignment_artifact)
    fps_processed = tracking_artifact["processing"]["fps_processed"]
    fps_original = io_artifact["video_properties"].get("fps_original") or fps_processed
    segments = io_artifact["processing"]["segments"]

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

    events = detect_pass_events(
        intervals=possession_intervals,
        fps_processed=fps_processed,
        fps_original=fps_original,
        min_control_seconds=min_pass_control_seconds,
        max_pass_gap_seconds=max_pass_gap_seconds,
        segments=segments,
        team_a_system=team_a_system,
        team_d_system=team_d_system,
    )

    team_a_name = team_name_for_system_team(io_artifact, team_a_system)
    team_d_name = team_name_for_system_team(io_artifact, team_d_system)

    return {
        "version": 1,
        "type": "system_pass_events",
        "videoId": io_artifact["video"]["video_id"],
        "videoFileName": io_artifact["video"]["file_name"],
        "videoDurationSeconds": io_artifact["video_properties"]["duration_seconds"],
        "teamAName": team_a_name,
        "teamDName": team_d_name,
        "teamMapping": {
            "teamA": team_a_system,
            "teamD": team_d_system,
        },
        "events": events,
        "statistics": count_events(events),
        "parameters": {
            "max_possession_distance_ratio": max_possession_distance_ratio,
            "min_possession_confirm_seconds": min_possession_confirm_seconds,
            "max_ball_missing_seconds": max_ball_missing_seconds,
            "use_ball_kalman_filter": use_ball_kalman_filter,
            "max_ball_interpolation_seconds": max_ball_interpolation_seconds,
            "min_pass_control_seconds": min_pass_control_seconds,
            "max_pass_gap_seconds": max_pass_gap_seconds,
        },
        "generatedFrom": {
            "ioArtifact": str(io_artifact_path).replace("\\", "/"),
            "trackingArtifact": str(tracking_artifact_path).replace("\\", "/"),
            "teamAssignmentArtifact": str(team_assignment_artifact_path).replace("\\", "/"),
        },
    }


def detect_pass_events(
    *,
    intervals: list[dict[str, Any]],
    fps_processed: float,
    fps_original: float,
    min_control_seconds: float,
    max_pass_gap_seconds: float,
    segments: list[dict[str, Any]],
    team_a_system: str,
    team_d_system: str,
) -> list[dict[str, Any]]:
    min_control_frames = _seconds_to_processed_frames(min_control_seconds, fps_processed, minimum=1)
    max_gap_frames = _seconds_to_processed_frames(max_pass_gap_seconds, fps_processed, minimum=0)
    controlled_intervals = _controlled_intervals(intervals, min_control_frames)
    events: list[dict[str, Any]] = []
    system_to_annotation_team = {
        team_a_system: "teamA",
        team_d_system: "teamD",
    }

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

        system_team = next_interval["team"]
        if system_team == UNKNOWN_TEAM or system_team not in system_to_annotation_team:
            continue

        frame = next_interval["start_frame"]
        time_seconds = round(frame / fps_original, 3)
        segment_name = _segment_name_for_frame(frame, segments)
        team = system_to_annotation_team[system_team]
        events.append(
            {
                "id": f"system-pass-{len(events) + 1}",
                "timeSeconds": time_seconds,
                "frame": frame,
                "team": team,
                "systemTeam": system_team,
                "fromTrackId": previous_interval["track_id"],
                "toTrackId": next_interval["track_id"],
                "previousControlStartFrame": previous_interval["start_frame"],
                "previousControlEndFrame": previous_interval["end_frame"],
                "receiverControlStartFrame": next_interval["start_frame"],
                "receiverControlEndFrame": next_interval["end_frame"],
                "gapFrames": gap_frames,
                "segmentName": segment_name,
            }
        )

    return events


def team_name_for_system_team(io_artifact: dict[str, Any], system_team: str) -> str:
    if system_team == "home":
        return io_artifact["match"]["home_team"]
    return io_artifact["match"]["away_team"]


def count_events(events: list[dict[str, Any]]) -> dict[str, int]:
    team_a_count = sum(1 for event in events if event["team"] == "teamA")
    team_d_count = sum(1 for event in events if event["team"] == "teamD")
    return {
        "teamACount": team_a_count,
        "teamDCount": team_d_count,
        "totalCount": team_a_count + team_d_count,
    }


if __name__ == "__main__":
    main()
