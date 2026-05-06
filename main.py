import argparse
import json
import cv2
from pathlib import Path

# get_video_metadata to be refactored to src/io"
def get_video_metadata(path: str) -> dict:
    if not Path(path).exists():
        raise FileNotFoundError(f"Video not found: {path}")
    
    cap = cv2.VideoCapture(path)
    
    if not cap.isOpened():
        raise IOError(f"Could not open video: {path}")

    # pull metadata
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_seconds = total_frames / fps

    cap.release() # release the video file from memory

    return {
        "total_frames": total_frames,
        "fps": fps,
        "width": width,
        "height": height,
        "duration_seconds": duration_seconds
    }

def save_metadata(metadata: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True) #create parent directories if they don't exist proceeds otherwise
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

def build_match_folder_name(date: str, team1: str, team2: str) -> str:
    safe_team1 = team1.replace(" ", "_")
    safe_team2 = team2.replace(" ", "_")
    return f"{date}_{team1}_vs_{team2}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to the video file")
    parser.add_argument("--team1", required=True, help="Name of the first team")
    parser.add_argument("--team2", required=True, help="Name of the second team")
    parser.add_argument("--half1-start", type=int, required=True, help="Start time of the first half")
    parser.add_argument("--half1-end", type=int, required=True, help="End time of the first half")
    parser.add_argument("--half2-start", type=int, required=True, help="Start time of the second half")
    parser.add_argument("--half2-end", type=int, required=True, help="End time of the second half")
    parser.add_argument("--team1-is-home", action="store_true", help="Flag to indicate if team1 is the home team")
    parser.add_argument("--date", required=True, help="Date of the match (YYYY-MM-DD)")
    
    args = parser.parse_args()

    video_metadata = get_video_metadata(args.input)

    if not (args.half1_start < args.half1_end <= args.half2_start < args.half2_end):
        parser.error(f"Half timestamps must be in order: half1_start {args.half1_start}s < half1_end {args.half1_end}s <= half2_start {args.half2_start}s < half2_end {args.half2_end}s")

    if args.half2_end > video_metadata["duration_seconds"]:
        parser.error(f"half2_end ({args.half2_end}s) exceeds video duration ({video_metadata['duration_seconds']:.0f}s)")

    metadata = {
        "video_filename": Path(args.input).name,
        "date": args.date,
        "team1": args.team1,
        "team2": args.team2,
        "team1_is_home": args.team1_is_home,
        "halves": {
            "half1": { "start_seconds": args.half1_start, "end_seconds": args.half1_end },
            "half2": { "start_seconds": args.half2_start, "end_seconds": args.half2_end }
        },
        "video_metadata": {
            "total_frames": video_metadata["total_frames"],
            "fps": video_metadata["fps"],
            "width": video_metadata["width"],
            "height": video_metadata["height"],
            "duration_seconds": video_metadata["duration_seconds"]
        },
    }

    folder_name = build_match_folder_name(args.date, args.team1, args.team2)
    output_path = Path("data/interim") / folder_name / "metadata.json"
    save_metadata(metadata, output_path)

    print(f"Metadata extracted and saved to {output_path}")
    print(json.dumps(metadata, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    exit(main())