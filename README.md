# BjaeverMetrics
BjaeverMetrics is a football analysis program designed for IF Frem Bjæverskov. It's developed as a CS finals project, and is built to be used by coaches for generating statistics from football videos to build winning strategies.

<div style="display:grid; grid-template-columns: 1fr 1fr 0.9fr; grid-auto-rows: min-content; gap:12px; align-items:start;">
	<img src="readme_screenshots\Screen Shot 2026-07-03 at 17.45.36.png" style="grid-column:1; grid-row:1 / span 2; width:100%; height:auto;" />
	<img src="readme_screenshots\Screen Shot 2026-07-03 at 17.43.40.png" style="grid-column:2; grid-row:1 / span 2; width:100%; height:auto;" />
	<img src="readme_screenshots\Screen Shot 2026-07-04 at 08.59.09.png" style="grid-column:3; grid-row:1; width:100%; height:auto;" />
</div> </br>

# Features
Automatic generation of possession and pass statistics


# Tech stack
- Python 3.14.0
- Ultralytics API
- React 18.3.1
<!-- - Pytest (check tests again and when validated add 'Pytest' back into 'Tech stack') -->


# Architecture
The system consists of a pipeline with four steps:
1. Video input and metadata extraction
2. Object detection and tracking using Ultralytics' API
3. Team assignment using k-means 
4. Statistics generation



# Getting started
A virtual environment is recommended so the dependencies don't interfere with other projects.

Create a Python virtual environment:
```
python -m venv .venv
```

Activate the environment:
```
.\.venv\Scripts\Activate.ps1
```

If you encounter errors while activating the environment, loosen the execution policy to allow PowerShell to activate the environment:
```
Set-ExectutionPolicy RemoteSigned
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the local API and serve the frontend:

```bash
uvicorn bjaevermetrics_app:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 in the browser.

Follow the UI guidance to analyze a video. 



Notes: 
- A relatively powerful GPU is required to analyze a video (it takes about 1.5 hours on an RTX 4070 Ti)
- The UI is in Danish only
- The system has been tested with Python 3.14.0, earlier versions have not been tested
- config/default.yaml contains config parameters used at runtime including object confidence thresholds, object detection model used, whether object detection runs on CPU or GPU, tracking algorithm used, stats output path, and more

# Authors
Githubs:  
[@CodingPhoque](https://github.com/CodingPhoque)  
[@kantsteen](https://github.com/kantsteen)