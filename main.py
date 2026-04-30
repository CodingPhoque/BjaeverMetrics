import argparse
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to the video file")

    args = parser.parse_args()

    metadata = get_video_metadata(args.input)
    print(f"File:       {args.input}")
    print(f"Frames:     {metadata['total_frames']}")
    print(f"FPS:        {metadata['fps']:.2f}")
    print(f"Resolution: {metadata['width']}x{metadata['height']}")
    print(f"Duration:   {metadata['duration_seconds']:.2f} seconds")

if __name__ == "__main__":
    exit(main())