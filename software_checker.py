"""Simple software detection program.
Performs basic environment and repo checks helpful before development.
"""
import sys
import os
import json
import subprocess

REPORT = {}

# Check Python version
REPORT['python_version'] = sys.version

# Check for venv
REPORT['venv_exists'] = os.path.isdir('.venv')

# Check for required files in parent project (NeuroMuscleAI-MVP)
PARENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'NeuroMuscleAI-MVP'))
REPORT['parent_exists'] = os.path.isdir(PARENT)
REPORT['parent_files'] = []
if REPORT['parent_exists']:
    try:
        REPORT['parent_files'] = os.listdir(PARENT)[:20]
    except Exception:
        REPORT['parent_files'] = []

# Check git status
try:
    out = subprocess.check_output(['git', 'status', '--porcelain'], stderr=subprocess.STDOUT, universal_newlines=True)
    REPORT['git_dirty'] = bool(out.strip())
except Exception as e:
    REPORT['git_dirty'] = f'git error: {e}'

# Write report
print(json.dumps(REPORT, indent=2, ensure_ascii=False))
