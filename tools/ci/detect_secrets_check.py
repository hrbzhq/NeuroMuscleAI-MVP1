#!/usr/bin/env python3
"""
Helper script for GitHub Actions: run detect-secrets in baseline-aware mode.
If .secrets.baseline exists, run detect-secrets with the baseline and write findings to tools/detect_secrets_findings.json.
Exit code 1 if new findings are present. If no baseline exists, create it and exit 1 so maintainers can review and commit it.
"""
import json
import os
import subprocess
import sys


def main():
    baseline = ".secrets.baseline"
    out = "tools/detect_secrets_findings.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)

    if os.path.isfile(baseline):
        # Some detect-secrets CLI versions support --json, others don't. Try variants.
        attempts = [
            ["detect-secrets", "scan", "--baseline", baseline, "--json"],
            ["detect-secrets", "scan", "--baseline", baseline],
            ["detect-secrets", "scan", "--json"],
            ["detect-secrets", "scan"],
        ]

        proc = None
        for cmd in attempts:
            try:
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            except FileNotFoundError:
                print("detect-secrets not found in PATH. Make sure it's installed.", file=sys.stderr)
                return 2

            # If command wrote something to stdout or stderr, break and inspect
            if (proc.stdout and proc.stdout.strip()) or (proc.stderr and proc.stderr.strip()):
                break

        if proc is None:
            print("Failed to run detect-secrets; no output captured.", file=sys.stderr)
            return 2

        # write raw output for artifact/debugging
        with open(out, "w", encoding="utf-8") as f:
            # prefer stdout, fallback to stderr
            f.write(proc.stdout or proc.stderr or "")

        # Try to parse JSON output if present
        data = {}
        try:
            data = json.loads(proc.stdout or proc.stderr or "{}")
        except json.JSONDecodeError:
            # Not JSON — attempt to detect if there are findings by simple heuristics
            text = (proc.stdout or proc.stderr or "").lower()
            if "no findings" in text or "no secrets" in text or "no detect-secrets findings" in text:
                print("No detect-secrets findings (heuristic)")
                return 0
            # If we can't parse, conservatively return 1 so CI shows failure for manual review
            print("detect-secrets output not JSON and parsing failed — failing for manual review.")
            return 1

        results = data.get("results", {})
        # results may be a dict mapping file -> list
        count = sum(len(v) for v in results.values()) if isinstance(results, dict) else 0
        if count > 0:
            print(f"Found {count} detect-secrets findings (new vs baseline)")
            for fname, items in list(results.items())[:10]:
                print(fname, '->', len(items), 'finding(s)')
            return 1
        else:
            print("No detect-secrets findings")
            return 0
    else:
        # First-time run: produce baseline and fail so humans can review.
        print("No .secrets.baseline found. Creating baseline and failing job for review.")
        cmd = ["detect-secrets", "scan"]
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except FileNotFoundError:
            print("detect-secrets not found in PATH. Make sure it's installed.", file=sys.stderr)
            return 2

        with open(baseline, "w", encoding="utf-8") as f:
            f.write(proc.stdout)
        print(f"Baseline written to {baseline}; please review and commit it before unblocking the workflow.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
