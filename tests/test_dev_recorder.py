import os
import time
import json
import tempfile

import sys
import os

# Ensure the project root (private scaffold) is on sys.path for imports
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import dev_recorder


def test_snapshot_and_record(tmp_path):
    # point logs to a tmp path
    orig_log = dev_recorder.LOG_PATH
    orig_env = dev_recorder.ENV_SNAPSHOT_PATH
    try:
        dev_recorder.LOG_PATH = os.path.join(tmp_path, 'dev_session.log')
        dev_recorder.ENV_SNAPSHOT_PATH = os.path.join(tmp_path, 'env_snapshot.json')
        # force a snapshot
        env = dev_recorder.snapshot_env()
        assert 'python' in env
        dev_recorder.record_command('echo test')
        dev_recorder.take_snapshot()
        # allow IO
        time.sleep(0.1)
        assert os.path.exists(dev_recorder.LOG_PATH)
        with open(dev_recorder.LOG_PATH, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        assert any('cmd' in l or 'snapshot' in l for l in lines)
    finally:
        dev_recorder.LOG_PATH = orig_log
        dev_recorder.ENV_SNAPSHOT_PATH = orig_env
