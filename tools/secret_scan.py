#!/usr/bin/env python3
"""Simple secret scanner for common keywords.

Usage: python tools/secret_scan.py
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(__file__))
PATTERNS = [
    r"password",
    r"passwd",
    r"secret",
    r"token",
    r"api[_-]?key",
    r"AKIA",
    r"PRIVATE_KEY",
    r"SECRET_KEY",
    r"gho_[A-Za-z0-9_]+",
    r"-----BEGIN PRIVATE KEY-----",
]

pat = re.compile("|".join(PATTERNS), re.IGNORECASE)

# directories to skip anywhere in the tree
SKIP_DIR_NAMES = {
    '.git', '.venv', 'venv', 'env', 'site-packages', 'node_modules',
    'build', 'dist', '.pytest_cache', '__pycache__'
}

# file extensions to ignore
SKIP_EXT = {'.png', '.jpg', '.jpeg', '.pyc', '.zip', '.bundle', '.tar', '.gz', '.woff', '.woff2'}
# also skip the scanner file itself and the tools directory
SKIP_PATH_PREFIXES = {os.path.join(ROOT, 'tools')}


def should_skip_path(path):
    # skip if any skip dir name is in the path
    parts = set(p for p in path.split(os.sep) if p)
    if parts & SKIP_DIR_NAMES:
        return True
    _, ext = os.path.splitext(path)
    if ext.lower() in SKIP_EXT:
        return True
    try:
        if os.path.getsize(path) > 1_000_000:  # skip files >1MB
            return True
    except Exception:
        pass
    return False


def scan():
    matches = []
    for root, dirs, files in os.walk(ROOT):
        # avoid descending into large/noisy directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES]
        for fn in files:
            path = os.path.join(root, fn)
            # skip files under tools/ and the scanner file itself
            if any(path.startswith(p) for p in SKIP_PATH_PREFIXES):
                continue
            if should_skip_path(path):
                continue
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f, 1):
                        if pat.search(line):
                            matches.append((path, i, line.strip()))
            except Exception:
                # ignore unreadable files
                continue
    return matches


if __name__ == '__main__':
    print('Running secret scan...')
    m = scan()
    if not m:
        print('No obvious matches found.')
    else:
        print(f'Found {len(m)} potential matches:')
        for path, lineno, snippet in m:
            print(f'{path}:{lineno}: {snippet[:200]}')
