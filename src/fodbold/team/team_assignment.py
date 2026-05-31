from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from sklearn.cluster import KMeans

from fodbold.io.metadata import validate_io_artifact
from fodbold.team.color_features import JerseyColorConfig, extract_jersey_color
from fodbold.tracking.tracker import validate_tracking_artifact

TEAM_ASSIGNMENT_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "interim_schemas"
    / "schemas"
    / "team_assignment_artifact.schema.json"
)

HEX_COLOR_PATTERN = re.compile(r"^#[a-fA-F0-9]{6}$")


def build_team_assignment_artifact(
    *,
    tracking_artifact_path: str | Path,
    home_team_color_hex: str,
    away_team_color_hex: str,
    color_space: str,
    min_fit_samples: int,
    min_observations_per_track: int,
    min_assignment_confidence: float,
    jersey_config: JerseyColorConfig,
) -> dict[str, Any]:
    color_space = color_space.strip().lower()
    if color_space != "lab":
        raise ValueError("Only lab color_space is currently supported for team assignment.")

    if min_observations_per_track < 1:
        raise ValueError("min_observations_per_track must be at least 1.")
    if not 0 <= min_assignment_confidence <= 1:
        raise ValueError("min_assignment_confidence must be between 0 and 1.")

    tracking_artifact_path = Path(tracking_artifact_path)
    tracking_artifact = load_tracking_artifact(tracking_artifact_path)
    io_artifact_path = _resolve_source_io_artifact_path(
        tracking_artifact["source_io_artifact"],
        tracking_artifact_path,
    )
    io_artifact = load_io_artifact(io_artifact_path)

    reference_colors = build_team_reference_colors(
        home_team_color_hex=home_team_color_hex,
        away_team_color_hex=away_team_color_hex,
        color_space=color_space,
    )
    observations, player_track_ids = extract_player_color_observations(
        tracking_artifact=tracking_artifact,
        io_artifact=io_artifact,
        jersey_config=jersey_config,
    )
    model = fit_team_clusters(
        observations,
        min_fit_samples=min_fit_samples,
    )
    clustered_observations = predict_observation_clusters(observations, model)
    cluster_votes = build_track_cluster_votes(clustered_observations, player_track_ids)
    cluster_to_team = map_clusters_to_teams(
        cluster_centers=model.cluster_centers_,
        reference_colors=reference_colors,
    )
    assigned_tracks, unassigned_tracks = assign_tracks_from_votes(
        track_votes=cluster_votes,
        min_observations_per_track=min_observations_per_track,
        min_assignment_confidence=min_assignment_confidence,
        cluster_to_team=cluster_to_team,
    )

    return {
        "artifact_type": "team_assignment",
        "schema_version": "1.0",
        "source_tracking_artifact": _to_artifact_path(tracking_artifact_path),
        "video_id": tracking_artifact["video_id"],
        "method": {
            "name": "kmeans",
            "color_space": color_space,
            "min_observations_per_track": min_observations_per_track,
            "min_assignment_confidence": min_assignment_confidence,
            "team_reference_colors": reference_colors,
            "clusters": build_cluster_summary(model.cluster_centers_, cluster_to_team),
        },
        "summary": {
            "player_tracks_total": len(player_track_ids),
            "player_tracks_assigned": len(assigned_tracks),
            "player_tracks_unassigned": len(unassigned_tracks),
            "player_observations_used": len(observations),
        },
        "assigned_tracks": assigned_tracks,
        "unassigned_tracks": unassigned_tracks,
    }


def load_tracking_artifact(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    validate_tracking_artifact(artifact)
    return artifact


def load_io_artifact(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    validate_io_artifact(artifact)
    return artifact


def save_team_assignment_artifact(artifact: dict[str, Any], output_path: str | Path) -> None:
    validate_team_assignment_artifact(artifact)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(artifact, file, indent=2, ensure_ascii=False)


def validate_team_assignment_artifact(
    artifact: dict[str, Any],
    schema_path: str | Path = TEAM_ASSIGNMENT_SCHEMA_PATH,
) -> None:
    schema_path = Path(schema_path)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    try:
        validator.validate(artifact)
    except ValidationError as error:
        raise ValueError(
            f"Team assignment artifact does not match schema: {error.message}"
        ) from error


def default_team_assignment_artifact_path(
    video_id: str,
    interim_dir: str | Path = "data/interim",
) -> Path:
    return Path(interim_dir) / f"{video_id}_team_assignment.json"


def build_team_reference_colors(
    *,
    home_team_color_hex: str,
    away_team_color_hex: str,
    color_space: str,
) -> dict[str, dict[str, Any]]:
    home_hex = _normalize_hex_color(home_team_color_hex)
    away_hex = _normalize_hex_color(away_team_color_hex)
    if home_hex.lower() == away_hex.lower():
        raise ValueError("home_team_color_hex and away_team_color_hex must be different.")

    return {
        "home": {
            "hex": home_hex,
            "color_value": _hex_to_color_value(home_hex, color_space),
        },
        "away": {
            "hex": away_hex,
            "color_value": _hex_to_color_value(away_hex, color_space),
        },
    }


def extract_player_color_observations(
    *,
    tracking_artifact: dict[str, Any],
    io_artifact: dict[str, Any],
    jersey_config: JerseyColorConfig,
) -> tuple[list[dict[str, Any]], set[int]]:
    frame_objects = {
        frame["frame_index"]: [
            tracked_object
            for tracked_object in frame["objects"]
            if _is_assignable_player_object(tracked_object)
        ]
        for frame in tracking_artifact["frames"]
    }
    frame_objects = {frame_index: objects for frame_index, objects in frame_objects.items() if objects}
    player_track_ids = {
        tracked_object["track_id"]
        for objects in frame_objects.values()
        for tracked_object in objects
    }

    observations = []
    for frame_index, frame in _iter_video_frames_by_index(
        io_artifact["video"]["path"],
        frame_objects.keys(),
    ):
        for tracked_object in frame_objects.get(frame_index, []):
            feature = extract_jersey_color(
                frame,
                tuple(tracked_object["bbox_xyxy"]),
                jersey_config,
            )
            if feature is None:
                continue

            observations.append(
                {
                    "track_id": tracked_object["track_id"],
                    "frame_index": frame_index,
                    "feature": np.asarray(feature, dtype=np.float32),
                }
            )

    return observations, player_track_ids


def fit_team_clusters(
    observations: list[dict[str, Any]],
    *,
    min_fit_samples: int,
    random_state: int = 0,
) -> KMeans:
    if len(observations) < min_fit_samples:
        raise ValueError(
            f"Need at least {min_fit_samples} valid player color observations, "
            f"got {len(observations)}"
        )

    features = np.array([observation["feature"] for observation in observations], dtype=np.float32)
    model = KMeans(n_clusters=2, n_init=10, random_state=random_state)
    model.fit(features)
    return model


def predict_observation_clusters(
    observations: list[dict[str, Any]],
    model: KMeans,
) -> list[dict[str, Any]]:
    clustered_observations = []

    for observation in observations:
        cluster_id = int(model.predict(observation["feature"].reshape(1, -1))[0])
        clustered_observations.append(
            {
                "track_id": observation["track_id"],
                "frame_index": observation["frame_index"],
                "cluster_id": cluster_id,
            }
        )

    return clustered_observations


def build_track_cluster_votes(
    clustered_observations: list[dict[str, Any]],
    player_track_ids: set[int],
) -> dict[int, dict[str, int]]:
    track_votes = {track_id: {"0": 0, "1": 0} for track_id in sorted(player_track_ids)}

    for observation in clustered_observations:
        track_votes[observation["track_id"]][str(observation["cluster_id"])] += 1

    return track_votes


def map_clusters_to_teams(
    *,
    cluster_centers: np.ndarray,
    reference_colors: dict[str, dict[str, Any]],
) -> dict[int, str]:
    centers = np.asarray(cluster_centers, dtype=np.float32)
    home_reference = np.asarray(reference_colors["home"]["color_value"], dtype=np.float32)
    away_reference = np.asarray(reference_colors["away"]["color_value"], dtype=np.float32)

    option_a_distance = np.linalg.norm(centers[0] - home_reference) + np.linalg.norm(
        centers[1] - away_reference
    )
    option_b_distance = np.linalg.norm(centers[0] - away_reference) + np.linalg.norm(
        centers[1] - home_reference
    )

    if option_a_distance <= option_b_distance:
        return {0: "home", 1: "away"}

    return {0: "away", 1: "home"}


def assign_tracks_from_votes(
    *,
    track_votes: dict[int, dict[str, int]],
    min_observations_per_track: int,
    min_assignment_confidence: float,
    cluster_to_team: dict[int, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    assigned_tracks = []
    unassigned_tracks = []

    for track_id, votes in sorted(track_votes.items()):
        observations_used = votes["0"] + votes["1"]

        if observations_used == 0:
            unassigned_tracks.append(
                _build_unassigned_track(track_id, "invalid_crops", observations_used, votes)
            )
            continue

        if observations_used < min_observations_per_track:
            unassigned_tracks.append(
                _build_unassigned_track(track_id, "too_few_observations", observations_used, votes)
            )
            continue

        majority_cluster_id, majority_votes = _majority_cluster(votes)
        confidence = majority_votes / observations_used
        if confidence < min_assignment_confidence:
            unassigned_tracks.append(
                _build_unassigned_track(track_id, "low_confidence", observations_used, votes)
            )
            continue

        assigned_tracks.append(
            {
                "track_id": track_id,
                "class_name": "player",
                "team": cluster_to_team[majority_cluster_id],
                "cluster_id": majority_cluster_id,
                "confidence": round(confidence, 4),
                "observations_used": observations_used,
                "cluster_votes": votes,
            }
        )

    return assigned_tracks, unassigned_tracks


def build_cluster_summary(
    cluster_centers: np.ndarray,
    cluster_to_team: dict[int, str],
) -> list[dict[str, Any]]:
    return [
        {
            "cluster_id": cluster_id,
            "center_color": [float(value) for value in cluster_centers[cluster_id]],
            "team": cluster_to_team[cluster_id],
        }
        for cluster_id in sorted(cluster_to_team)
    ]


def _is_assignable_player_object(tracked_object: dict[str, Any]) -> bool:
    return (
        tracked_object["class_name"] == "player"
        and isinstance(tracked_object["track_id"], int)
    )


def _iter_video_frames_by_index(
    video_path: str | Path,
    frame_indexes: Iterable[int],
) -> Iterator[tuple[int, Any]]:
    sorted_frame_indexes = sorted(set(frame_indexes))
    if not sorted_frame_indexes:
        return

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise OSError(f"Could not open video: {video_path}")

    current_frame_index: int | None = None
    try:
        for target_frame_index in sorted_frame_indexes:
            if current_frame_index is None or target_frame_index < current_frame_index:
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_index)
                current_frame_index = target_frame_index

            if target_frame_index - current_frame_index > 10:
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_index)
                current_frame_index = target_frame_index

            while current_frame_index < target_frame_index:
                ok, _ = cap.read()
                if not ok:
                    break
                current_frame_index += 1

            if current_frame_index != target_frame_index:
                continue

            ok, frame = cap.read()
            if not ok:
                continue

            current_frame_index += 1
            yield target_frame_index, frame
    finally:
        cap.release()


def _build_unassigned_track(
    track_id: int,
    reason: str,
    observations_used: int,
    cluster_votes: dict[str, int],
) -> dict[str, Any]:
    return {
        "track_id": track_id,
        "class_name": "player",
        "reason": reason,
        "observations_used": observations_used,
        "cluster_votes": cluster_votes,
    }


def _majority_cluster(votes: dict[str, int]) -> tuple[int, int]:
    vote_counter = Counter({0: votes["0"], 1: votes["1"]})
    cluster_id, vote_count = vote_counter.most_common(1)[0]
    return int(cluster_id), int(vote_count)


def _normalize_hex_color(hex_color: str) -> str:
    normalized = hex_color.strip()
    if not HEX_COLOR_PATTERN.fullmatch(normalized):
        raise ValueError(f"Expected hex color like '#1f5fbf', got {hex_color!r}")

    return normalized


def _hex_to_color_value(hex_color: str, color_space: str) -> list[float]:
    if color_space != "lab":
        raise ValueError("Only lab color_space is currently supported for team assignment.")

    red = int(hex_color[1:3], 16)
    green = int(hex_color[3:5], 16)
    blue = int(hex_color[5:7], 16)
    bgr_pixel = np.uint8([[[blue, green, red]]])
    lab_pixel = cv2.cvtColor(bgr_pixel, cv2.COLOR_BGR2LAB)[0, 0]
    return [float(value) for value in lab_pixel]


def _resolve_source_io_artifact_path(
    source_io_artifact: str,
    tracking_artifact_path: Path,
) -> Path:
    source_path = Path(source_io_artifact)
    if source_path.exists() or source_path.is_absolute():
        return source_path

    sibling_path = tracking_artifact_path.parent / source_path.name
    if sibling_path.exists():
        return sibling_path

    return source_path


def _to_artifact_path(path: Path) -> str:
    return str(path).replace("\\", "/")
