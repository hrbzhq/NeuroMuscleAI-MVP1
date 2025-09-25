NeuroMuscleAI-MVP1

Minimal scaffold for NeuroMuscleAI-MVP1. Includes two helper tools:
- software_checker.py: simple static checks and environment validation
- dev_recorder.py: runtime logger that records development session actions

Run the checker and recorder before development.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Files

- `dev_recorder.py` — session recorder (JSONL + rotation)
- `software_checker.py` — environment checker
- `app.py` — minimal Streamlit demo that exercises recorder & checker

Logs

- `dev_session.log` — JSONL event log
- `env_snapshot.json` — environment snapshot
