from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from fodbold.team.color_features import (  # noqa: E402
    crop_jersey_region,
    extract_lab_feature_without_grass,
)


@dataclass(slots=True)
class JerseyCropExample:
    frame_index: int
    class_name: str
    confidence: float
    bbox_xyxy: tuple[float, float, float, float]
    crop_bgr: np.ndarray
    feature_lab: np.ndarray


@dataclass(slots=True)
class SpikeStats:
    detections_by_class: dict[str, int] = field(default_factory=dict)
    rejected_empty_crop: int = 0
    rejected_no_feature: int = 0

    def count_detection(self, class_name: str, amount: int) -> None:
        self.detections_by_class[class_name] = self.detections_by_class.get(class_name, 0) + amount


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Spike: cluster player jersey colors with KMeans."
    )
    parser.add_argument("--video", required=True, help="Path to video file")
    parser.add_argument(
        "--config",
        default="configs/default.yaml",
        help="Path to config YAML",
    )
    parser.add_argument(
        "--output-dir",
        default="data/debug/team_spike",
        help="Directory where spike images and summaries are saved",
    )
    parser.add_argument(
        "--max-sampled-frames",
        type=int,
        default=200,
        help="Maximum sampled frames to run detection on",
    )
    parser.add_argument(
        "--frame-stride",
        type=int,
        default=15,
        help="Process every Nth frame",
    )
    parser.add_argument(
        "--min-player-crops",
        type=int,
        default=50,
        help="Minimum player crops required before fitting KMeans",
    )
    parser.add_argument(
        "--examples-per-cluster",
        type=int,
        default=24,
        help="How many representative crops to save per cluster",
    )
    parser.add_argument(
        "--device",
        default=None,
        help='Override detection device, for example "cpu" or "cuda"',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    from fodbold.config import Config
    from fodbold.detection.detector import FootballDetector

    config_path = (REPO_ROOT / args.config).resolve()
    video_path = Path(args.video).resolve()
    output_dir = (REPO_ROOT / args.output_dir).resolve()

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    config = Config.load(config_path)
    if args.device is not None:
        config.detection.device = args.device

    detector = FootballDetector(
        config=config.detection,
        models_dir=REPO_ROOT / config.paths["models_dir"],
    )
    print(f"Model classes: {detector.model.names}")

    output_dir.mkdir(parents=True, exist_ok=True)

    player_examples: list[JerseyCropExample] = []
    referee_examples: list[JerseyCropExample] = []
    goalkeeper_examples: list[JerseyCropExample] = []

    sampled_frames, stats = collect_examples(
        video_path=video_path,
        detector=detector,
        max_sampled_frames=args.max_sampled_frames,
        frame_stride=args.frame_stride,
        player_examples=player_examples,
        referee_examples=referee_examples,
        goalkeeper_examples=goalkeeper_examples,
    )

    if len(player_examples) < args.min_player_crops:
        raise RuntimeError(
            f"Only collected {len(player_examples)} player crops. "
            f"Need at least {args.min_player_crops}.\n"
            f"Sampled frames: {sampled_frames}\n"
            f"Detections by class after detector filtering: {stats.detections_by_class}\n"
            f"Rejected empty/small jersey crops: {stats.rejected_empty_crop}\n"
            f"Rejected crops without enough non-grass pixels: {stats.rejected_no_feature}\n"
            "If detections_by_class is empty, check model class names and confidence thresholds."
        )

    features = np.vstack([example.feature_lab for example in player_examples])
    centers_lab, labels = fit_kmeans_2(features)
    distances = np.linalg.norm(features - centers_lab[labels], axis=1)

    save_cluster_outputs(
        output_dir=output_dir,
        player_examples=player_examples,
        labels=labels,
        distances=distances,
        centers_lab=centers_lab,
        examples_per_cluster=args.examples_per_cluster,
    )
    save_contact_sheet(
        referee_examples[: args.examples_per_cluster],
        output_dir / "referees_yolo_class.jpg",
    )
    save_contact_sheet(
        goalkeeper_examples[: args.examples_per_cluster],
        output_dir / "goalkeepers_yolo_class.jpg",
    )
    save_features_csv(output_dir / "player_features.csv", player_examples, labels, distances)
    save_summary(
        output_dir=output_dir,
        args=args,
        sampled_frames=sampled_frames,
        player_examples=player_examples,
        referee_examples=referee_examples,
        goalkeeper_examples=goalkeeper_examples,
        labels=labels,
        centers_lab=centers_lab,
        stats=stats,
    )

    print(f"Saved KMeans spike output to: {output_dir}")
    print(f"Player crops: {len(player_examples)}")
    print(f"Cluster counts: {np.bincount(labels, minlength=2).tolist()}")
    return 0


def collect_examples(
    video_path: Path,
    detector: Any,
    max_sampled_frames: int,
    frame_stride: int,
    player_examples: list[JerseyCropExample],
    referee_examples: list[JerseyCropExample],
    goalkeeper_examples: list[JerseyCropExample],
) -> tuple[int, SpikeStats]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise OSError(f"Could not open video: {video_path}")

    frame_index = 0
    sampled_frames = 0
    stats = SpikeStats()

    try:
        while sampled_frames < max_sampled_frames:
            ok, frame = cap.read()
            if not ok:
                break

            if frame_index % frame_stride != 0:
                frame_index += 1
                continue

            detections = detector.detect(frame)
            add_examples(frame, frame_index, detections.players, player_examples, stats)
            add_examples(frame, frame_index, detections.referees, referee_examples, stats)
            add_examples(frame, frame_index, detections.goalkeepers, goalkeeper_examples, stats)

            sampled_frames += 1
            frame_index += 1
    finally:
        cap.release()

    return sampled_frames, stats


def add_examples(
    frame: np.ndarray,
    frame_index: int,
    detections: list[Any],
    examples: list[JerseyCropExample],
    stats: SpikeStats,
) -> None:
    if detections:
        stats.count_detection(detections[0].class_name, len(detections))

    for detection in detections:
        crop = crop_jersey_region(frame, detection.bbox_xyxy)
        if crop is None:
            stats.rejected_empty_crop += 1
            continue

        feature = extract_lab_feature_without_grass(crop)
        if feature is None:
            stats.rejected_no_feature += 1
            continue

        examples.append(
            JerseyCropExample(
                frame_index=frame_index,
                class_name=detection.class_name,
                confidence=detection.confidence,
                bbox_xyxy=detection.bbox_xyxy,
                crop_bgr=crop,
                feature_lab=feature,
            )
        )


def fit_kmeans_2(
    features: np.ndarray,
    max_iterations: int = 50,
    random_seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    if len(features) < 2:
        raise ValueError("At least 2 features are required for k=2 clustering.")

    rng = np.random.default_rng(random_seed)
    center_indices = rng.choice(len(features), size=2, replace=False)
    centers = features[center_indices].astype(np.float32)

    for _ in range(max_iterations):
        distances = np.linalg.norm(features[:, None, :] - centers[None, :, :], axis=2)
        labels = np.argmin(distances, axis=1)

        new_centers = centers.copy()
        for cluster_id in range(2):
            cluster_features = features[labels == cluster_id]
            if len(cluster_features) > 0:
                new_centers[cluster_id] = np.mean(cluster_features, axis=0)

        if np.allclose(centers, new_centers):
            break

        centers = new_centers

    distances = np.linalg.norm(features[:, None, :] - centers[None, :, :], axis=2)
    labels = np.argmin(distances, axis=1)
    return centers, labels


def save_cluster_outputs(
    output_dir: Path,
    player_examples: list[JerseyCropExample],
    labels: np.ndarray,
    distances: np.ndarray,
    centers_lab: np.ndarray,
    examples_per_cluster: int,
) -> None:
    for cluster_id in range(2):
        indices = np.where(labels == cluster_id)[0]
        representative_indices = sorted(indices, key=lambda index: distances[index])
        selected = [player_examples[index] for index in representative_indices[:examples_per_cluster]]
        save_contact_sheet(selected, output_dir / f"team_cluster_{cluster_id}.jpg")

    save_center_swatch(output_dir / "cluster_center_colors.jpg", centers_lab)


def save_contact_sheet(
    examples: list[JerseyCropExample],
    output_path: Path,
    thumb_size: tuple[int, int] = (96, 128),
    columns: int = 6,
) -> None:
    if not examples:
        return

    thumb_width, thumb_height = thumb_size
    rows = int(np.ceil(len(examples) / columns))
    sheet = np.full(
        (rows * thumb_height, columns * thumb_width, 3),
        fill_value=255,
        dtype=np.uint8,
    )

    for index, example in enumerate(examples):
        row = index // columns
        column = index % columns
        resized = cv2.resize(example.crop_bgr, thumb_size, interpolation=cv2.INTER_AREA)
        label = f"f{example.frame_index} {example.confidence:.2f}"
        cv2.putText(
            resized,
            label,
            (4, 14),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.35,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        y1 = row * thumb_height
        x1 = column * thumb_width
        sheet[y1 : y1 + thumb_height, x1 : x1 + thumb_width] = resized

    cv2.imwrite(str(output_path), sheet)


def save_center_swatch(output_path: Path, centers_lab: np.ndarray) -> None:
    centers_lab_uint8 = np.clip(centers_lab, 0, 255).astype(np.uint8).reshape(1, -1, 3)
    centers_bgr = cv2.cvtColor(centers_lab_uint8, cv2.COLOR_LAB2BGR)
    swatch = np.repeat(np.repeat(centers_bgr, 120, axis=0), 180, axis=1)
    cv2.imwrite(str(output_path), swatch)


def save_features_csv(
    output_path: Path,
    examples: list[JerseyCropExample],
    labels: np.ndarray,
    distances: np.ndarray,
) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            [
                "frame_index",
                "class_name",
                "confidence",
                "bbox_x1",
                "bbox_y1",
                "bbox_x2",
                "bbox_y2",
                "cluster",
                "distance_to_center",
                "lab_l",
                "lab_a",
                "lab_b",
            ]
        )
        for example, label, distance in zip(examples, labels, distances, strict=True):
            writer.writerow(
                [
                    example.frame_index,
                    example.class_name,
                    example.confidence,
                    *example.bbox_xyxy,
                    int(label),
                    float(distance),
                    *example.feature_lab.tolist(),
                ]
            )


def save_summary(
    output_dir: Path,
    args: argparse.Namespace,
    sampled_frames: int,
    player_examples: list[JerseyCropExample],
    referee_examples: list[JerseyCropExample],
    goalkeeper_examples: list[JerseyCropExample],
    labels: np.ndarray,
    centers_lab: np.ndarray,
    stats: SpikeStats,
) -> None:
    summary = {
        "video": str(Path(args.video).resolve()),
        "sampled_frames": sampled_frames,
        "frame_stride": args.frame_stride,
        "player_crops": len(player_examples),
        "referee_crops": len(referee_examples),
        "goalkeeper_crops": len(goalkeeper_examples),
        "detections_by_class_after_filtering": stats.detections_by_class,
        "rejected_empty_or_small_jersey_crops": stats.rejected_empty_crop,
        "rejected_crops_without_enough_non_grass_pixels": stats.rejected_no_feature,
        "cluster_counts": {
            "cluster_0": int(np.count_nonzero(labels == 0)),
            "cluster_1": int(np.count_nonzero(labels == 1)),
        },
        "cluster_centers_lab": centers_lab.tolist(),
        "outputs": {
            "cluster_0_examples": "team_cluster_0.jpg",
            "cluster_1_examples": "team_cluster_1.jpg",
            "cluster_center_colors": "cluster_center_colors.jpg",
            "player_features": "player_features.csv",
            "referee_examples": "referees_yolo_class.jpg",
            "goalkeeper_examples": "goalkeepers_yolo_class.jpg",
        },
    }

    with open(output_dir / "summary.json", "w", encoding="utf-8") as summary_file:
        json.dump(summary, summary_file, indent=2)


if __name__ == "__main__":
    raise SystemExit(main())
