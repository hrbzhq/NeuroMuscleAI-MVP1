import os
import time
import gzip

from recorder_io import write_record_raw, rotate_if_needed


def test_write_and_rotate(tmp_path):
    log = os.path.join(tmp_path, "dev_session.log")
    # write small record
    write_record_raw({"type": "test", "payload": "a"}, log, max_bytes=100, backup_count=2)
    assert os.path.exists(log)
    # write more to exceed rotation threshold
    for i in range(20):
        write_record_raw({"type": "test", "payload": "x" * 50}, log, max_bytes=200, backup_count=2)
    # force rotate check
    rotate_if_needed(log, max_bytes=200, backup_count=2)
    # check for rotated gz files
    gz = [p for p in os.listdir(tmp_path) if p.endswith('.gz')]
    assert len(gz) >= 1
    # ensure gz is valid
    gzpath = os.path.join(tmp_path, gz[0])
    with gzip.open(gzpath, 'rb') as f:
        data = f.read()
    assert b"test" in data
