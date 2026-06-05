from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from ultralytics import YOLO
from ultralytics.engine.results import Boxes
from ultralytics.trackers.bot_sort import BOTSORT
from ultralytics.trackers.byte_tracker import BYTETracker
from ultralytics.utils import YAML, IterableSimpleNamespace
from ultralytics.utils.checks import check_yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from fodbold.config import Config  # noqa: E402


@dataclass(frozen=True)
class CachedDetections:
    frame_index: int
    boxes_xyxy_conf_cls: np.ndarray
    orig_shape: tuple[int, int]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare ByteTrack and BoT-SORT runtime on the same cached YOLO detections. "
            "This is a throwaway benchmarking script, not part of the production pipeline."
        )
    )
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "configs" / "default.yaml")
    parser.add_argument("--video", type=Path, default=PROJECT_ROOT / "data" / "raw" / "Serie_4_Ringsted_IF.mp4")
    parser.add_argument("--model", type=Path, default=None)
    parser.add_argument("--start-seconds", type=float, default=600.0)
    parser.add_argument("--duration-seconds", type=float, default=30.0)
    parser.add_argument("--fps-target", type=float, default=None)
    parser.add_argument("--imgsz", type=int, default=320)
    parser.add_argument("--device", default=None)
    parser.add_argument("--conf", type=float, default=0.25)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = Config.load(args.config)
    video_path = resolve_path(args.video)
    model_path = resolve_path(
        args.model
        if args.model is not None
        else PROJECT_ROOT / config.paths["models_dir"] / config.detection.model_file
    )
    device = args.device if args.device is not None else config.detection.device
    fps_target = args.fps_target if args.fps_target is not None else config.video.fps_target

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    clip_info = read_clip_info(
        video_path=video_path,
        start_seconds=args.start_seconds,
        duration_seconds=args.duration_seconds,
        fps_target=fps_target,
    )

    print("Benchmark clip")
    print(f"- video: {video_path}")
    print(f"- model: {model_path}")
    print(f"- start_seconds: {args.start_seconds}")
    print(f"- duration_seconds: {args.duration_seconds}")
    print(f"- fps_original: {clip_info['fps_original']:.3f}")
    print(f"- frame_stride: {clip_info['frame_stride']}")
    print(f"- frames_to_process: {len(clip_info['frame_indices'])}")
    print(f"- imgsz: {args.imgsz}")
    print(f"- device: {device}")
    print(f"- detection_conf: {args.conf}")
    print()

    model = YOLO(str(model_path))

    detection_start = time.perf_counter()
    cached_detections = cache_detections(
        model=model,
        video_path=video_path,
        frame_indices=clip_info["frame_indices"],
        imgsz=args.imgsz,
        device=device,
        conf=args.conf,
    )
    detection_seconds = time.perf_counter() - detection_start
    total_detections = sum(len(item.boxes_xyxy_conf_cls) for item in cached_detections)

    print("Detection cache")
    print(f"- seconds: {detection_seconds:.3f}")
    print(f"- cached_frames: {len(cached_detections)}")
    print(f"- cached_detections: {total_detections}")
    print()

    results = []
    for tracker_name in ("bytetrack", "botsort"):
        tracker_result = run_tracker_benchmark(
            tracker_name=tracker_name,
            video_path=video_path,
            cached_detections=cached_detections,
            frame_rate=max(1, round(clip_info["fps_processed"])),
        )
        results.append(tracker_result)

    print("Tracker-only runtime")
    for result in results:
        print(f"- {result['tracker']}:")
        print(f"  seconds: {result['seconds']:.6f}")
        print(f"  ms_per_frame: {result['ms_per_frame']:.4f}")
        print(f"  output_tracks_total: {result['output_tracks_total']}")

    if len(results) == 2:
        bytetrack = results[0]["seconds"]
        botsort = results[1]["seconds"]
        ratio = botsort / bytetrack if bytetrack > 0 else float("inf")
        print()
        print(f"BoT-SORT / ByteTrack runtime ratio: {ratio:.2f}x")

    return 0


def resolve_path(path: str | Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def read_clip_info(
    *,
    video_path: Path,
    start_seconds: float,
    duration_seconds: float,
    fps_target: float,
) -> dict[str, Any]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise OSError(f"Could not open video: {video_path}")
    try:
        fps_original = float(cap.get(cv2.CAP_PROP_FPS))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    finally:
        cap.release()

    if fps_original <= 0:
        raise ValueError(f"Video FPS must be greater than 0, got {fps_original}")
    if fps_target <= 0:
        raise ValueError(f"fps_target must be greater than 0, got {fps_target}")

    frame_stride = max(1, int(round(fps_original / fps_target)))
    start_frame = int(round(start_seconds * fps_original))
    end_frame = min(frame_count, int(round((start_seconds + duration_seconds) * fps_original)))
    if not 0 <= start_frame < end_frame <= frame_count:
        raise ValueError(
            f"Invalid clip frames {start_frame=} {end_frame=} for video with {frame_count} frames."
        )

    return {
        "fps_original": fps_original,
        "fps_processed": fps_original / frame_stride,
        "frame_stride": frame_stride,
        "frame_indices": list(range(start_frame, end_frame, frame_stride)),
    }


def cache_detections(
    *,
    model: YOLO,
    video_path: Path,
    frame_indices: list[int],
    imgsz: int,
    device: str,
    conf: float,
) -> list[CachedDetections]:
    cached = []
    for position, (frame_index, frame) in enumerate(
        iter_video_frames_by_index(video_path, frame_indices),
        start=1,
    ):
        result = model.predict(
            frame,
            conf=conf,
            imgsz=imgsz,
            device=device,
            verbose=False,
        )[0]
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            data = np.empty((0, 6), dtype=np.float32)
        else:
            data = boxes.data.cpu().numpy().astype(np.float32, copy=True)

        cached.append(
            CachedDetections(
                frame_index=frame_index,
                boxes_xyxy_conf_cls=data,
                orig_shape=tuple(result.orig_shape),
            )
        )

        if position == 1 or position % 100 == 0 or position == len(frame_indices):
            print(f"cached detections: {position}/{len(frame_indices)} frames")

    return cached


def run_tracker_benchmark(
    *,
    tracker_name: str,
    video_path: Path,
    cached_detections: list[CachedDetections],
    frame_rate: int,
) -> dict[str, Any]:
    tracker = build_tracker(tracker_name, frame_rate=frame_rate)
    cached_by_frame = {item.frame_index: item for item in cached_detections}
    frame_indices = [item.frame_index for item in cached_detections]

    update_seconds = 0.0
    output_tracks_total = 0

    for frame_index, frame in iter_video_frames_by_index(video_path, frame_indices):
        cached = cached_by_frame[frame_index]
        boxes = Boxes(cached.boxes_xyxy_conf_cls.copy(), cached.orig_shape)

        start = time.perf_counter()
        tracks = tracker.update(boxes, frame)
        update_seconds += time.perf_counter() - start

        output_tracks_total += len(tracks)

    frame_count = len(cached_detections)
    return {
        "tracker": tracker_name,
        "seconds": update_seconds,
        "ms_per_frame": (update_seconds / frame_count) * 1000 if frame_count else 0.0,
        "output_tracks_total": output_tracks_total,
    }


def build_tracker(tracker_name: str, *, frame_rate: int) -> BYTETracker | BOTSORT:
    tracker_yaml = check_yaml(f"{tracker_name}.yaml")
    cfg = IterableSimpleNamespace(**YAML.load(tracker_yaml))
    if tracker_name == "bytetrack":
        return BYTETracker(args=cfg, frame_rate=frame_rate)
    if tracker_name == "botsort":
        return BOTSORT(args=cfg, frame_rate=frame_rate)
    raise ValueError(f"Unsupported tracker: {tracker_name}")


def iter_video_frames_by_index(
    video_path: Path,
    frame_indices: list[int],
):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise OSError(f"Could not open video: {video_path}")

    sorted_indices = sorted(set(frame_indices))
    current_frame_index: int | None = None
    try:
        for target_frame_index in sorted_indices:
            if current_frame_index is None or target_frame_index < current_frame_index:
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_index)
                current_frame_index = target_frame_index

            if target_frame_index - current_frame_index > 10:
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_index)
                current_frame_index = target_frame_index

            while current_frame_index < target_frame_index:
                ok, _ = cap.read()
                if not ok:
                    return
                current_frame_index += 1

            ok, frame = cap.read()
            if not ok:
                return

            current_frame_index += 1
            yield target_frame_index, frame
    finally:
        cap.release()


if __name__ == "__main__":
    raise SystemExit(main())
