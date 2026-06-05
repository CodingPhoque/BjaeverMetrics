from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

ULTRALYTICS_CONFIG_DIR = PROJECT_ROOT / "data" / "ultralytics"
ULTRALYTICS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(ULTRALYTICS_CONFIG_DIR))

from database.db import (  # noqa: E402
    DATABASE_PATH,
    create_tables,
    load_match,
    load_matches,
    save_stats_artifact,
    video_id_exists,
)
from fodbold.config import Config  # noqa: E402
from fodbold.io.metadata import build_video_id  # noqa: E402
from fodbold.pipeline import run_pipeline  # noqa: E402

FRONTEND_DIR = PROJECT_ROOT / "frontend"
RAW_UPLOAD_DIR = PROJECT_ROOT / "data" / "raw"
CONFIG_PATH = PROJECT_ROOT / "configs" / "default.yaml"

app = FastAPI(title="BjaeverMetrics Local API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def disable_frontend_cache(request, call_next):
    response = await call_next(request)
    if not request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def open_database() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    create_tables(connection)
    return connection


@app.get("/api/matches")
def api_matches():
    with open_database() as connection:
        return load_matches(connection)


@app.post("/api/analyze")
def api_analyze(
    video: UploadFile = File(...),
    date: str = Form(...),
    home_team: str = Form(...),
    away_team: str = Form(...),
    home_color: str = Form(...),
    away_color: str = Form(...),
    venue: str = Form(""),
    half1_start_seconds: float = Form(...),
    half1_end_seconds: float = Form(...),
    half2_start_seconds: float = Form(...),
    half2_end_seconds: float = Form(...),
    goals_home: int = Form(0),
    goals_away: int = Form(0),
    shots_on_target_home: int = Form(0),
    shots_on_target_away: int = Form(0),
):
    video_id = build_video_id(date, home_team, away_team)

    with open_database() as connection:
        if video_id_exists(connection, video_id):
            raise HTTPException(
                status_code=409,
                detail="Denne kamp/video findes allerede i databasen.",
            )

    suffix = Path(video.filename or "").suffix or ".mp4"
    RAW_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    video_path = RAW_UPLOAD_DIR / f"{video_id}{suffix}"
    with video_path.open("wb") as file:
        shutil.copyfileobj(video.file, file)

    try:
        config = Config.load(CONFIG_PATH)
        artifact_paths = run_pipeline(
            video_path=video_path,
            date=date,
            home_team=home_team,
            away_team=away_team,
            half1_start_seconds=half1_start_seconds,
            half1_end_seconds=half1_end_seconds,
            half2_start_seconds=half2_start_seconds,
            half2_end_seconds=half2_end_seconds,
            home_team_color_hex=home_color,
            away_team_color_hex=away_color,
            goals_home=goals_home,
            goals_away=goals_away,
            shots_on_target_home=shots_on_target_home,
            shots_on_target_away=shots_on_target_away,
            venue=venue or None,
            video_id=video_id,
            config=config,
            project_root=PROJECT_ROOT,
        )
        stats_path = artifact_paths["stats"]
        artifact = json.loads(stats_path.read_text(encoding="utf-8"))
        with open_database() as connection:
            try:
                match_id = save_stats_artifact(
                    connection,
                    artifact,
                    home_color=home_color,
                    away_color=away_color,
                )
            except sqlite3.IntegrityError as error:
                if "matches.video_id" in str(error) or "UNIQUE constraint failed" in str(error):
                    raise HTTPException(
                        status_code=409,
                        detail="Denne kamp/video findes allerede i databasen.",
                    ) from error
                raise
            match = load_match(connection, match_id)
            connection.commit()
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    return {"match": match}


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
