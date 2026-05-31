from __future__ import annotations

from pathlib import Path

from fodbold.config import Config
from fodbold.io.metadata import build_io_artifact, save_io_artifact
from fodbold.stats.stats import (
    build_stats_artifact,
    default_stats_artifact_path,
    save_stats_artifact,
)
from fodbold.team.team_assignment import (
    build_team_assignment_artifact,
    default_team_assignment_artifact_path,
    save_team_assignment_artifact,
)
from fodbold.tracking.tracker import (
    build_tracking_artifact,
    default_tracking_artifact_path,
    save_tracking_artifact,
)


def run_pipeline(
    *,
    video_path: str | Path,
    date: str,
    home_team: str,
    away_team: str,
    half1_start_seconds: float,
    half1_end_seconds: float,
    half2_start_seconds: float,
    half2_end_seconds: float,
    home_team_color_hex: str,
    away_team_color_hex: str,
    goals_home: int,
    goals_away: int,
    shots_on_target_home: int,
    shots_on_target_away: int,
    config: Config,
    project_root: str | Path = ".",
    venue: str | None = None,
    video_id: str | None = None,
) -> dict[str, Path]:
    if not config.team_classification.enabled:
        raise ValueError("team_classification.enabled must be true to run the full pipeline.")

    io_artifact_path = run_io_stage(
        video_path=video_path,
        date=date,
        home_team=home_team,
        away_team=away_team,
        half1_start_seconds=half1_start_seconds,
        half1_end_seconds=half1_end_seconds,
        half2_start_seconds=half2_start_seconds,
        half2_end_seconds=half2_end_seconds,
        config=config,
        project_root=project_root,
        venue=venue,
        video_id=video_id,
    )
    tracking_artifact_path = run_tracking_stage(
        io_artifact_path=io_artifact_path,
        config=config,
        project_root=project_root,
    )
    team_assignment_artifact_path = run_team_assignment_stage(
        tracking_artifact_path=tracking_artifact_path,
        home_team_color_hex=home_team_color_hex,
        away_team_color_hex=away_team_color_hex,
        config=config,
        project_root=project_root,
    )
    stats_artifact_path = run_stats_stage(
        io_artifact_path=io_artifact_path,
        tracking_artifact_path=tracking_artifact_path,
        team_assignment_artifact_path=team_assignment_artifact_path,
        goals_home=goals_home,
        goals_away=goals_away,
        shots_on_target_home=shots_on_target_home,
        shots_on_target_away=shots_on_target_away,
        config=config,
        project_root=project_root,
    )

    return {
        "io": io_artifact_path,
        "tracking": tracking_artifact_path,
        "team_assignment": team_assignment_artifact_path,
        "stats": stats_artifact_path,
    }


def run_io_stage(
    *,
    video_path: str | Path,
    date: str,
    home_team: str,
    away_team: str,
    half1_start_seconds: float,
    half1_end_seconds: float,
    half2_start_seconds: float,
    half2_end_seconds: float,
    config: Config,
    project_root: str | Path = ".",
    fps_target: float | None = None,
    venue: str | None = None,
    video_id: str | None = None,
    output_path: str | Path | None = None,
) -> Path:
    project_root = Path(project_root)
    resolved_video_path = _resolve_project_path(video_path, project_root)
    interim_dir = _resolve_project_path(config.paths["interim_dir"], project_root)

    artifact = build_io_artifact(
        video_path=resolved_video_path,
        date=date,
        home_team=home_team,
        away_team=away_team,
        half1_start_seconds=half1_start_seconds,
        half1_end_seconds=half1_end_seconds,
        half2_start_seconds=half2_start_seconds,
        half2_end_seconds=half2_end_seconds,
        fps_target=fps_target if fps_target is not None else config.video.fps_target,
        venue=venue,
        video_id=video_id,
    )

    resolved_output_path = (
        _resolve_project_path(output_path, project_root)
        if output_path
        else default_io_artifact_path(artifact["video"]["video_id"], interim_dir)
    )
    save_io_artifact(artifact, resolved_output_path)
    return resolved_output_path


def default_io_artifact_path(
    video_id: str,
    interim_dir: str | Path = "data/interim",
) -> Path:
    return Path(interim_dir) / f"{video_id}_io.json"


def run_tracking_stage(
    *,
    io_artifact_path: str | Path,
    config: Config,
    project_root: str | Path = ".",
    output_path: str | Path | None = None,
) -> Path:
    project_root = Path(project_root)
    model_path = _resolve_project_path(
        Path(config.paths["models_dir"]) / config.detection.model_file,
        project_root,
    )
    interim_dir = _resolve_project_path(config.paths["interim_dir"], project_root)
    tracker_name = config.tracking.algorithm.strip().lower()
    tracker_config = f"{tracker_name}.yaml"

    artifact = build_tracking_artifact(
        io_artifact_path=io_artifact_path,
        model_path=model_path,
        tracker_name=tracker_name,
        tracker_config=tracker_config,
        device=config.detection.device,
        image_size=config.detection.image_size,
        confidence_thresholds=config.detection.confidence_threshold,
    )

    resolved_output_path = Path(output_path) if output_path else default_tracking_artifact_path(
        artifact["video_id"],
        interim_dir,
    )
    save_tracking_artifact(artifact, resolved_output_path)
    return resolved_output_path


def run_team_assignment_stage(
    *,
    tracking_artifact_path: str | Path,
    home_team_color_hex: str,
    away_team_color_hex: str,
    config: Config,
    project_root: str | Path = ".",
    output_path: str | Path | None = None,
) -> Path:
    project_root = Path(project_root)
    resolved_tracking_artifact_path = _resolve_project_path(
        tracking_artifact_path,
        project_root,
    )
    interim_dir = _resolve_project_path(config.paths["interim_dir"], project_root)

    artifact = build_team_assignment_artifact(
        tracking_artifact_path=resolved_tracking_artifact_path,
        home_team_color_hex=home_team_color_hex,
        away_team_color_hex=away_team_color_hex,
        color_space=config.team_classification.color_space,
        min_fit_samples=config.team_classification.min_fit_samples,
        min_observations_per_track=config.team_classification.min_observations_per_track,
        min_assignment_confidence=config.team_classification.min_assignment_confidence,
        jersey_config=config.team_classification.to_jersey_color_config(),
    )

    resolved_output_path = (
        _resolve_project_path(output_path, project_root)
        if output_path
        else default_team_assignment_artifact_path(artifact["video_id"], interim_dir)
    )
    save_team_assignment_artifact(artifact, resolved_output_path)
    return resolved_output_path


def run_stats_stage(
    *,
    io_artifact_path: str | Path,
    tracking_artifact_path: str | Path,
    team_assignment_artifact_path: str | Path,
    goals_home: int,
    goals_away: int,
    shots_on_target_home: int,
    shots_on_target_away: int,
    config: Config,
    project_root: str | Path = ".",
    output_path: str | Path | None = None,
) -> Path:
    project_root = Path(project_root)
    resolved_io_artifact_path = _resolve_project_path(io_artifact_path, project_root)
    resolved_tracking_artifact_path = _resolve_project_path(tracking_artifact_path, project_root)
    resolved_team_assignment_artifact_path = _resolve_project_path(
        team_assignment_artifact_path,
        project_root,
    )
    interim_dir = _resolve_project_path(config.paths["interim_dir"], project_root)

    artifact = build_stats_artifact(
        io_artifact_path=resolved_io_artifact_path,
        tracking_artifact_path=resolved_tracking_artifact_path,
        team_assignment_artifact_path=resolved_team_assignment_artifact_path,
        goals_home=goals_home,
        goals_away=goals_away,
        shots_on_target_home=shots_on_target_home,
        shots_on_target_away=shots_on_target_away,
        max_possession_distance_ratio=(
            config.stats.possession.max_possession_distance_ratio
        ),
        min_possession_confirm_seconds=(
            config.stats.possession.min_possession_confirm_seconds
        ),
        max_ball_missing_seconds=config.stats.possession.max_ball_missing_seconds,
        use_ball_kalman_filter=config.stats.possession.use_ball_kalman_filter,
        max_ball_interpolation_seconds=(
            config.stats.possession.max_ball_interpolation_seconds
        ),
        min_pass_control_seconds=config.stats.passes.min_control_seconds,
        max_pass_gap_seconds=config.stats.passes.max_pass_gap_seconds,
        min_turnover_control_seconds=config.stats.turnovers.min_control_seconds,
        max_turnover_gap_seconds=config.stats.turnovers.max_turnover_gap_seconds,
    )

    resolved_output_path = (
        _resolve_project_path(output_path, project_root)
        if output_path
        else default_stats_artifact_path(artifact["video_id"], interim_dir)
    )
    save_stats_artifact(artifact, resolved_output_path)
    return resolved_output_path


def _resolve_project_path(path: str | Path, project_root: Path) -> Path:
    resolved_path = Path(path)
    if resolved_path.is_absolute():
        return resolved_path

    return project_root / resolved_path
