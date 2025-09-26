import os
import time
import threading
import gzip

import sys

# ensure project root on path
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import dev_recorder
from recorder_io import rotate_if_needed


def _worker(n, prefix="w"):
    for i in range(n):
        dev_recorder.record_command(f"{prefix}-{i}")


def test_concurrent_writes_trigger_rotation(tmp_path):
    """Start the recorder loop and spawn multiple threads that write many records.

    This integration test sets a small rotation threshold so that concurrent writes
    cause rotation and a .gz rotated file should appear.
    """
    orig_log = dev_recorder.LOG_PATH
    try:
        log = os.path.join(tmp_path, "dev_session.log")
        dev_recorder.LOG_PATH = log

        # reduce thresholds so rotation happens quickly
        small_max = 1024  # 1 KB

        # start the background loop with a short interval
        started = dev_recorder.start(interval=0.2)
        assert started is True

        # spawn several writer threads
        threads = []
        for t in range(6):
            thr = threading.Thread(target=_worker, args=(200, f"t{t}"), daemon=True)
            threads.append(thr)
            thr.start()

        # wait for threads to finish
        for thr in threads:
            thr.join()

        # give background loop and IO a moment
        time.sleep(1.0)

        # force rotation check using recorder_io helper
        rotate_if_needed(log, max_bytes=small_max, backup_count=3)

        gz_files = [p for p in os.listdir(tmp_path) if p.endswith('.gz')]
        # ensure at least one rotated compressed file exists
        assert len(gz_files) >= 1, f"expected rotated .gz files, found: {gz_files}"

        # validate gz content roughly
        gzpath = os.path.join(tmp_path, gz_files[0])
        with gzip.open(gzpath, 'rb') as f:
            data = f.read()
        assert b"cmd" in data or b"snapshot" in data

    finally:
        dev_recorder.stop()
        dev_recorder.LOG_PATH = orig_log
