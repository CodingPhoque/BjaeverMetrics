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
    ensure_columns(connection)


def ensure_columns(connection):
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(matches)").fetchall()
    }
    if "home_color" not in columns:
        connection.execute("ALTER TABLE matches ADD COLUMN home_color TEXT")
    if "away_color" not in columns:
        connection.execute("ALTER TABLE matches ADD COLUMN away_color TEXT")


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


def save_stats_artifact(connection, artifact, home_color=None, away_color=None):
    match = artifact["match"]

    cursor = connection.execute(
        """
        INSERT INTO matches (
            video_id,
            match_date,
            home_team,
            away_team,
            home_color,
            away_color,
            venue
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact["video_id"],
            match["date"],
            match["home_team"],
            match["away_team"],
            home_color,
            away_color,
            match["venue"],
        ),
    )

    match_id = cursor.lastrowid

    for metric_name, metric in artifact["stats"].items():
        save_stat_row(connection, match_id, metric_name, "total", metric)

        for segment in metric.get("by_segment", []):
            save_stat_row(connection, match_id, metric_name, segment["segment_name"], metric, segment)

    return match_id


def video_id_exists(connection, video_id):
    row = connection.execute(
        "SELECT 1 FROM matches WHERE video_id = ?",
        (video_id,),
    ).fetchone()
    return row is not None


def load_matches(connection):
    rows = connection.execute(
        """
        SELECT id, video_id, match_date, home_team, away_team, home_color, away_color, venue
        FROM matches
        ORDER BY match_date, id
        """
    ).fetchall()
    return [load_match(connection, row[0], row) for row in rows]


def load_match(connection, match_id, match_row=None):
    if match_row is None:
        match_row = connection.execute(
            """
            SELECT id, video_id, match_date, home_team, away_team, home_color, away_color, venue
            FROM matches
            WHERE id = ?
            """,
            (match_id,),
        ).fetchone()

    if match_row is None:
        return None

    (
        db_id,
        video_id,
        match_date,
        home_team,
        away_team,
        home_color,
        away_color,
        venue,
    ) = match_row

    stats = {}
    stat_rows = connection.execute(
        """
        SELECT metric_name, segment_name, home_value, away_value, unknown_value
        FROM match_stats
        WHERE match_id = ?
        ORDER BY metric_name, segment_name
        """,
        (db_id,),
    ).fetchall()

    for metric_name, segment_name, home, away, unknown in stat_rows:
        metric = stats.setdefault(metric_name, {})
        values = {
            "home": _clean_number(home),
            "away": _clean_number(away),
        }
        if unknown is not None:
            values["unknown"] = _clean_number(unknown)

        if segment_name == "total":
            metric.update(values)
        elif segment_name == "first_half":
            metric["h1"] = values
        elif segment_name == "second_half":
            metric["h2"] = values
        else:
            metric[segment_name] = values

    return {
        "id": str(db_id),
        "videoId": video_id,
        "date": match_date,
        "homeTeam": home_team,
        "awayTeam": away_team,
        "homeColor": home_color or "#d62839",
        "awayColor": away_color or "#1d6fe0",
        "venue": venue or "",
        "stats": stats,
    }


def _clean_number(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


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
