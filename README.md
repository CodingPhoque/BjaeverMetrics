# BjaeverMetrics
BjaeverMetrics is an advanced football analysis program designed for IF Frem Bjæverskov. It is used by coaches for advanced statistic to build winning strategies.

Run pip install -r requirement.txt

## Local web app

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the local API and frontend:

```bash
uvicorn bjaevermetrics_app:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 in the browser.

The local app serves `frontend/`, receives video uploads at `POST /api/analyze`,
runs the pipeline on the local machine, stores results in SQLite, and shows saved
matches through `GET /api/matches`.




BJEAVERMETRICS/
├── .venv/
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── README.md
│
├── configs/
│   ├── default.yaml          # default runtime config
│   └── test.yaml             # overrides for --test mode
│
├── data/                     # gitignored (large files)
│   ├── raw/                  # original Veo MP4s
│   ├── annotated/            # your labeled frames for fine-tuning - training data/benchmarking data
│   ├── interim/              # detections.json, tracking.json per match
│   ├── processed/            # final stats.json/parquet
│   └── models/               # best.pt, pretrained weights
│
├── src/
│   └── fodbold/              # your package
│       ├── __init__.py
│       ├── config.py         # load + validate config
│       ├── cli.py            # argparse/typer logic (called by main.py)
│       │
│       ├── io/
│       │   ├── __init__.py
│       │   ├── video.py      # OpenCV reader, frame iterator
│       │   └── metadata.py   # holdnavne, halvleg, hjemme/ude
│       │
│       ├── detection/
│       │   ├── __init__.py
│       │   └── detector.py   # YOLO wrapper
│       │
│       ├── tracking/
│       │   ├── __init__.py
│       │   └── tracker.py    # ByteTrack/BoT-SORT wrapper
│       │
│       ├── stats/
│       │   ├── __init__.py
│       │   ├── possession.py
│       │   ├── touches.py
│       │   └── passes.py
│       │
│       └── pipeline.py       # orchestrates the stages
│
├── tests/
│   ├── __init__.py
│   ├── test_video.py
│   ├── test_detector.py
│   └── fixtures/             # tiny test clips
│
├── notebooks/                # spikes, model comparisons, exploration
│   
│
├── scripts/                  # one-off utilities
│   
│
└── main.py                   # thin CLI wrapper → src/fodbold/cli.py
