#!/usr/bin/env python3
"""Parse a detect-secrets JSON output and print a compact summary for reviewers."""
import json
import sys


def summarize(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to load {path}: {e}")
        return 2

    results = data.get('results') or {}
    total = sum(len(v) for v in results.values())
    print(f"Total findings: {total}\n")

    for fname, items in results.items():
        print(f"{fname}: {len(items)} finding(s)")
        for it in items:
            secret_type = it.get('type') or it.get('secret_type') or 'unknown'
            line = it.get('line_number') or it.get('line') or ''
            print(f"  - {secret_type} @ {line}")
        print()

    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: parse_detect_findings.py <detect_secrets_json>")
        sys.exit(2)
    sys.exit(summarize(sys.argv[1]))
