# Secret-scan workflow

This document explains the secret-scan GitHub Actions workflow and how to triage findings.

Workflow overview
- Location: `.github/workflows/secret-scan.yml`
- Runs on: push to `main`, `master`, `open-source/prep` and on pull requests
- Steps:
  1. Checkout repository
  2. Run `tools/secret_scan.py` (regex scanner)
  3. Run `gitleaks` action
  4. Install `detect-secrets` and run `tools/ci/detect_secrets_check.py`
  5. Upload artifacts (`tools/detect_secrets_findings.json` and `tools/secret_scan_output.txt`) on failure

Triage process
1. Inspect the uploaded artifacts from the failed workflow run.
2. Run `python tools/ci/parse_detect_findings.py tools/detect_secrets_findings.json` locally to get a compact summary.
3. Classify findings as: false positive / test data / real secret.
4. For false positives, add exceptions to the baseline and commit the updated `.secrets.baseline`.
5. For real secrets, rotate and purge from history, then re-run scans to confirm remediation.

Need help?
If you'd like, I can:
- Add an Action that posts a summarized comment on PRs with the findings.
- Prepare an initial reviewed `.secrets.baseline` candidate in a draft PR for maintainers to inspect.
