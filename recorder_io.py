"""I/O and rotation helpers for dev_recorder.

Provides small, testable functions to write JSONL lines and rotate/compress logs.
All functions accept an explicit log_path to make testing easier.
"""
from __future__ import annotations

import json
import os
import shutil
import glob
import gzip
from datetime import datetime
from typing import Dict, Optional


def _now_ts() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def rotate_if_needed(log_path: str, max_bytes: int = 5 * 1024 * 1024, backup_count: int = 7) -> None:
    try:
        if not os.path.exists(log_path):
            return
        size = os.path.getsize(log_path)
        if size <= max_bytes:
            return
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        dst = f"{log_path}.{ts}"
        try:
            os.rename(log_path, dst)
        except Exception:
            shutil.copy2(log_path, dst)
            with open(log_path, "w", encoding="utf-8"):
                pass
        # compress
        try:
            with open(dst, "rb") as f_in:
                with gzip.open(dst + ".gz", "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            try:
                os.remove(dst)
            except Exception:
                pass
        except Exception:
            pass
        # prune
        pattern = f"{log_path}.*.gz"
        files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        for old in files[backup_count:]:
            try:
                os.remove(old)
            except Exception:
                continue
    except Exception:
        return


def write_record_raw(record: Dict, log_path: str, max_bytes: int = 5 * 1024 * 1024, backup_count: int = 7) -> None:
    try:
        rotate_if_needed(log_path, max_bytes=max_bytes, backup_count=backup_count)
        line = json.dumps(record, ensure_ascii=False)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # best effort
        return


def force_rotate(log_path: str, max_bytes: int = 5 * 1024 * 1024, backup_count: int = 7) -> None:
    rotate_if_needed(log_path, max_bytes=max_bytes, backup_count=backup_count)
