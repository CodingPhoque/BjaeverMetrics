from __future__ import annotations

import argparse
import json
from pathlib import Path

from fodbold.config import Config
from fodbold.pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the BjaeverMetrics video pipeline.")
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    parser.add_argument("--input", required=True, help="Path to the video file")
    parser.add_argument("--home-team", required=True, help="Name of the home team")
    parser.add_argument("--away-team", required=True, help="Name of the away team")
    parser.add_argument("--home-team-color", required=True, help="Home team shirt color as hex")
    parser.add_argument("--away-team-color", required=True, help="Away team shirt color as hex")
    parser.add_argument("--date", required=True, help="Date of the match (YYYY-MM-DD)")
    parser.add_argument("--venue", default=None, help="Optional match venue")
    parser.add_argument("--half1-start", type=float, required=True)
    parser.add_argument("--half1-end", type=float, required=True)
    parser.add_argument("--half2-start", type=float, required=True)
    parser.add_argument("--half2-end", type=float, required=True)
    parser.add_argument("--goals-home", type=int, required=True)
    parser.add_argument("--goals-away", type=int, required=True)
    parser.add_argument("--shots-on-target-home", type=int, required=True)
    parser.add_argument("--shots-on-target-away", type=int, required=True)
    parser.add_argument("--video-id", default=None)
    return parser


# Can either take a list of arguments or rely on sys.argv as default (None = None)
def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # run_pipeline, build_io_artifact and get_video_metadata raise exceptions
    # try-exception block catches them and prints user-friendly error messages
    try:
        config = Config.load(args.config)
        # If output paths are not provided as arguments, run_pipeline uses default paths and file names based on video_id
        # run_pipeline saves each artifact to its output path
        artifact_paths = run_pipeline(
            video_path=args.input,
            date=args.date,
            home_team=args.home_team,
            away_team=args.away_team,
            half1_start_seconds=args.half1_start,
            half1_end_seconds=args.half1_end,
            half2_start_seconds=args.half2_start,
            half2_end_seconds=args.half2_end,
            home_team_color_hex=args.home_team_color,
            away_team_color_hex=args.away_team_color,
            goals_home=args.goals_home,
            goals_away=args.goals_away,
            shots_on_target_home=args.shots_on_target_home,
            shots_on_target_away=args.shots_on_target_away,
            venue=args.venue,
            video_id=args.video_id,
            config=config,
        )
    except (FileNotFoundError, ImportError, OSError, ValueError, KeyError) as error:
        parser.error(str(error))

    print("Pipeline artifacts saved:")
    print(
        json.dumps(
            {name: str(path) for name, path in artifact_paths.items()},
            indent=2,
            ensure_ascii=False,
        )
    )

    # Explicitly return 0 to indicate successful execution of main()
    return 0
