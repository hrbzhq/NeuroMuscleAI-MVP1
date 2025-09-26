"""Development session recorder.

This enhanced recorder writes session metadata and periodic snapshots to a rolling
log file in the project directory. Features:

- environment variable snapshot (at start and on demand)
- attempts to read common shell history files (bash/zsh/fish and PowerShell PSReadLine)
- keep in-memory recent command history and API to record commands explicitly
- periodic snapshots with CPU/memory/disk and top processes (uses psutil if available)
- start()/stop() API and a simple CLI for running in foreground

The module is intentionally conservative about external dependencies: if ``psutil`` is
not available it will still run and provide basic disk/cpu info where possible.
"""

from __future__ import annotations

import json
import os
import time
import threading
import shutil
import platform
import glob
import gzip
from collections import deque
from datetime import datetime, timezone
from typing import Deque, Dict, Optional

try:
    # when running as a package
    from . import recorder_io
except Exception:
    # when running tests or direct import where package context is not set
    import recorder_io

LOG_PATH = os.path.join(os.path.dirname(__file__), "dev_session.log")
ENV_SNAPSHOT_PATH = os.path.join(os.path.dirname(__file__), "env_snapshot.json")
DEFAULT_INTERVAL = 10
# Rotation settings
MAX_LOG_BYTES = int(os.environ.get("DEV_RECORDER_MAX_BYTES", 5 * 1024 * 1024))  # 5 MB default
BACKUP_COUNT = int(os.environ.get("DEV_RECORDER_BACKUP_COUNT", 7))
_running = False
_thread: Optional[threading.Thread] = None
_lock = threading.Lock()
recent_commands: Deque[str] = deque(maxlen=500)

try:
    import psutil

    _HAS_PSUTIL = True
except Exception:
    psutil = None  # type: ignore
    _HAS_PSUTIL = False


def _now() -> str:
    # use timezone-aware UTC ISO timestamps
    return datetime.now(timezone.utc).isoformat()


def _write_log(entry: str) -> None:
    # Deprecated string writer kept for backwards compatibility; prefer _write_record
    _write_record_raw({"type": "note", "msg": entry})


def _rotate_log_if_needed() -> None:
    # delegate to recorder_io with configured params
    recorder_io.rotate_if_needed(LOG_PATH, max_bytes=MAX_LOG_BYTES, backup_count=BACKUP_COUNT)


def _write_record_raw(record: Dict) -> None:
    """Write a pre-built record dict to the log as a JSON line (JSONL)."""
    try:
        # delegate actual I/O to recorder_io (keeps this module testable)
        recorder_io.write_record_raw(record, LOG_PATH, max_bytes=MAX_LOG_BYTES, backup_count=BACKUP_COUNT)
    except Exception:
        # Best-effort: swallow errors to avoid crashing the recorder
        return


def force_rotate() -> None:
    """Public API to force rotation/compression immediately."""
    recorder_io.force_rotate(LOG_PATH, max_bytes=MAX_LOG_BYTES, backup_count=BACKUP_COUNT)
    _write_record("rotation", {"action": "forced"})


def _write_record(event_type: str, payload) -> None:
    rec = {
        "timestamp": _now(),
        "type": event_type,
        "payload": payload,
    }
    _write_record_raw(rec)


def snapshot_env() -> Dict[str, str]:
    """Capture a snapshot of relevant environment variables and write to a file.

    Returns the environment dict captured.
    """
    env = dict(os.environ)
    minimal = {
        "timestamp": _now(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "env": {k: v for k, v in env.items()},
    }
    try:
        with open(ENV_SNAPSHOT_PATH, "w", encoding="utf-8") as f:
            json.dump(minimal, f, indent=2, ensure_ascii=False)
    except Exception as e:
        _write_record("env-snapshot-error", {"error": str(e)})
    _write_record("env-snapshot", {"path": ENV_SNAPSHOT_PATH})
    return minimal


def _read_history_files() -> Dict[str, str]:
    """Try to read common shell history files and return mapping filename->contents.

    This is best-effort and will ignore inaccessible files.
    """
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, ".bash_history"),
        os.path.join(home, ".zsh_history"),
        os.path.join(home, ".local/share/fish/fish_history"),
        os.path.join(home, ".config/fish/fish_history"),
    ]
    # PowerShell PSReadLine history location (Windows)
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(os.path.join(appdata, "Microsoft", "Windows", "PowerShell", "PSReadLine", "ConsoleHost_history.txt"))

    found = {}
    for p in candidates:
        try:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    # don't store full content in main log; keep size metadata and a small sample
                    found[p] = {"size": len(content), "sample": content[-1024:]}
        except Exception as e:
            _write_record("history-read-error", {"path": p, "error": str(e)})
    return found


def record_command(cmd: str) -> None:
    """Record a command to the recent history and append to the log.

    Call this from tools or wrappers that want to annotate the session with explicit commands.
    """
    recent_commands.appendleft(cmd)
    _write_record("cmd", {"cmd": cmd})


def _gather_system_snapshot(top_n: int = 5) -> Dict:
    data: Dict = {"timestamp": _now()}
    try:
        if _HAS_PSUTIL and psutil:
            data.update(
                {
                    "cpu_percent": psutil.cpu_percent(interval=None),
                    "cpu_count": psutil.cpu_count(logical=True),
                    "memory_percent": psutil.virtual_memory().percent,
                    "memory_total": psutil.virtual_memory().total,
                    "disk": {},
                }
            )
            for part in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    data["disk"][part.mountpoint] = {
                        "total": usage.total,
                        "used": usage.used,
                        "percent": usage.percent,
                    }
                except Exception:
                    continue

            procs = []
            for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                try:
                    info = p.info
                    procs.append(info)
                except Exception:
                    continue
            procs_sorted = sorted(procs, key=lambda x: x.get("cpu_percent", 0), reverse=True)[:top_n]
            data["top_processes"] = procs_sorted
        else:
            # Fallbacks when psutil isn't installed
            data.update({
                "cpu_count": os.cpu_count(),
                "cpu_percent": None,
                "memory_percent": None,
                "disk": {},
            })
            try:
                for mount in [os.path.splitdrive(os.getcwd())[0] + os.sep]:
                    try:
                        usage = shutil.disk_usage(mount)
                        data["disk"][mount] = {"total": usage.total, "used": usage.used}
                    except Exception:
                        continue
            except Exception:
                pass
            data["top_processes"] = "psutil not installed; top processes unavailable"
    except Exception as e:
        data["error"] = str(e)
    return data


def take_snapshot() -> None:
    """Take a system snapshot and append it to the log as JSON."""
    snap = _gather_system_snapshot()
    try:
        _write_record("snapshot", snap)
    except Exception as e:
        _write_record("snapshot-error", {"error": str(e)})


def _recorder_loop(interval: int) -> None:
    _write_record("session-start", {"interval": interval})
    # initial snapshots
    snapshot_env()
    histories = _read_history_files()
    for p, content in histories.items():
        _write_record("history-file", {"path": p, "meta": content})

    while _running:
        try:
            take_snapshot()
            # optionally log recent commands summary
            if recent_commands:
                with _lock:
                    sample = list(recent_commands)[:10]
                _write_record("recent-cmds", {"commands": sample})
        except Exception as e:
            _write_log(f"[loop-error] {_now()} {e}")
        time.sleep(interval)


def start(interval: int = DEFAULT_INTERVAL) -> bool:
    """Start the background recorder loop. Returns True if started, False if already running."""
    global _running, _thread
    if _running:
        return False
    _running = True
    _thread = threading.Thread(target=_recorder_loop, args=(interval,), daemon=True)
    _thread.start()
    return True


def stop() -> None:
    """Stop the background recorder and write a session stop marker."""
    global _running, _thread
    _running = False
    if _thread is not None:
        _thread.join(timeout=2)
    _write_record("session-stop", {})


def get_recent_commands(n: int = 20) -> list:
    """Return up to `n` most recent recorded commands."""
    with _lock:
        return list(recent_commands)[:n]


def cli_main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the development session recorder")
    parser.add_argument("--interval", "-i", type=int, default=DEFAULT_INTERVAL, help="snapshot interval seconds")
    parser.add_argument("--once", action="store_true", help="take one snapshot and exit")
    args = parser.parse_args()

    if args.once:
        snapshot_env()
        take_snapshot()
        print("Snapshot written to log.")
        return

    print(f"Starting dev recorder (logging to {LOG_PATH}) with interval={args.interval}s. Ctrl-C to stop.")
    start(args.interval)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop()
        print("Stopped recorder.")


if __name__ == "__main__":
    cli_main()
