import argparse
import json
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "database" / "bjavermetrics.sqlite"
SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"
EXAMPLE_ARTIFACT_PATH = (
    PROJECT_ROOT / "interim_schemas" / "examples" / "stats_artifact.example.json"
)


def create_tables(connection):
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    connection.executescript(schema)


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def resolve_project_path(path):
    path = Path(path)
    if path.is_absolute():
        return path

    if path.exists():
        return path

    return PROJECT_ROOT / path


def save_stats_artifact(connection, artifact):
    match = artifact["match"]

    cursor = connection.execute(
        """
        INSERT INTO matches (
            video_id,
            match_date,
            home_team,
            away_team,
            venue
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            artifact["video_id"],
            match["date"],
            match["home_team"],
            match["away_team"],
            match["venue"],
        ),
    )

    match_id = cursor.lastrowid

    for metric_name, metric in artifact["stats"].items():
        save_stat_row(connection, match_id, metric_name, "total", metric)

        for segment in metric.get("by_segment", []):
            save_stat_row(connection, match_id, metric_name, segment["segment_name"], metric, segment)

    return match_id


def save_stat_row(connection, match_id, metric_name, segment_name, metric, segment=None):
    values = segment if segment is not None else metric

    connection.execute(
        """
        INSERT INTO match_stats (
            match_id,
            metric_name,
            segment_name,
            unit,
            source,
            home_value,
            away_value,
            unknown_value
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            match_id,
            metric_name,
            segment_name,
            metric["unit"],
            metric["source"],
            values["home"],
            values["away"],
            values.get("unknown"),
        ),
    )


def print_saved_stats(connection, match_id):
    rows = connection.execute(
        """
        SELECT metric_name, segment_name, home_value, away_value, unknown_value
        FROM match_stats
        WHERE match_id = ?
        ORDER BY metric_name, segment_name
        """,
        (match_id,),
    ).fetchall()

    print(f"Inserted {len(rows)} stat rows:")
    for metric_name, segment_name, home, away, unknown in rows:
        print(f"- {metric_name} / {segment_name}: home={home}, away={away}, unknown={unknown}")


def reset_database_file(database_path):
    if database_path.exists():
        database_path.unlink()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", default=EXAMPLE_ARTIFACT_PATH)
    parser.add_argument("--database", default=DATABASE_PATH)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    database_path = resolve_project_path(args.database)
    artifact_path = resolve_project_path(args.artifact)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    if args.reset:
        reset_database_file(database_path)

    artifact = load_json(artifact_path)

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        create_tables(connection)
        match_id = save_stats_artifact(connection, artifact)
        print(f"Saved match_id={match_id} in {database_path}")
        print_saved_stats(connection, match_id)


if __name__ == "__main__":
    main()
