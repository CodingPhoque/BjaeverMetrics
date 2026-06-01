PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL UNIQUE,
    match_date TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_color TEXT,
    away_color TEXT,
    venue TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS match_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    metric_name TEXT NOT NULL,
    segment_name TEXT NOT NULL,
    unit TEXT NOT NULL,
    source TEXT NOT NULL,
    home_value REAL NOT NULL,
    away_value REAL NOT NULL,
    unknown_value REAL,
    FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
    UNIQUE (match_id, metric_name, segment_name)
);

