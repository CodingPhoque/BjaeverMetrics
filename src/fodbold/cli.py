from __future__ import annotations

import argparse
import json
from pathlib import Path

from fodbold.io.metadata import build_io_artifact, save_io_artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a BjaeverMetrics IO artifact.")
    parser.add_argument("--input", required=True, help="Path to the video file")
    parser.add_argument("--home-team", required=True, help="Name of the home team")
    parser.add_argument("--away-team", required=True, help="Name of the away team")
    parser.add_argument("--date", required=True, help="Date of the match (YYYY-MM-DD)")
    parser.add_argument("--venue", default=None, help="Optional match venue")
    parser.add_argument("--half1-start", type=float, required=True)
    parser.add_argument("--half1-end", type=float, required=True)
    parser.add_argument("--half2-start", type=float, required=True)
    parser.add_argument("--half2-end", type=float, required=True)
    parser.add_argument("--fps-target", type=float, default=30.0)
    parser.add_argument("--video-id", default=None)
    parser.add_argument("--output", type=Path, default=None)
    return parser


# Can either take a list of arguments or rely on sys.argv as default (None = None)
def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # build_io_artifact and get_video_metadata raise exceptions
    # try-exception block catches them and prints user-friendly error messages
    try:
        artifact = build_io_artifact(
            video_path=args.input,
            date=args.date,
            home_team=args.home_team,
            away_team=args.away_team,
            half1_start_seconds=args.half1_start,
            half1_end_seconds=args.half1_end,
            half2_start_seconds=args.half2_start,
            half2_end_seconds=args.half2_end,
            fps_target=args.fps_target,
            venue=args.venue,
            video_id=args.video_id,
        )
    except (FileNotFoundError, ImportError, OSError, ValueError) as error:
        parser.error(str(error))

    # If output path is not provided as argument, use default path and file name based on video_id
    # Save the artifact to the output path
    output_path = args.output or _default_io_artifact_path(artifact)
    save_io_artifact(artifact, output_path)

    print(f"IO artifact saved to {output_path}")
    print(json.dumps(artifact, indent=2, ensure_ascii=False))

    # Explicitly return 0 to indicate successful execution of main()
    return 0


def _default_io_artifact_path(artifact: dict) -> Path:
    video_id = artifact["video"]["video_id"]
    return Path("data/interim") / f"{video_id}_io.json"
