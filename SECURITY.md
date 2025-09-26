# Security scanning and secret baseline policy

This repository includes automated secret scanning in CI to help prevent accidental credential leaks.

Key points
- A GitHub Actions workflow `.github/workflows/secret-scan.yml` runs three checks on push and PRs:
  - a lightweight repo regex scanner (`tools/secret_scan.py`)
  - `gitleaks` (via the `zricethezav/gitleaks-action` action)
  - `detect-secrets` (baseline-aware) driven by `tools/ci/detect_secrets_check.py`

- The detect-secrets helper will create a `.secrets.baseline` on first run and intentionally fail the job so maintainers can review findings before committing the baseline.
- Do NOT commit `.secrets.baseline` until one or more maintainers have manually reviewed the findings and confirmed that none are real secrets. If there are real secrets, rotate them and purge them from git history before committing.

How to run scans locally

1. From the repository root, activate your virtualenv and install detect-secrets:

```powershell
& .\.venv_torch\Scripts\Activate.ps1
pip install --upgrade detect-secrets
```

2. Run the quick repo regex scanner (writes `tools/secret_scan_output.txt`):

```powershell
python tools\secret_scan.py | Tee-Object tools\secret_scan_output.txt
notepad tools\secret_scan_output.txt
```

3. Run the baseline-aware detect-secrets helper (it will create `.secrets.baseline` on first run and exit non-zero):

```powershell
python tools\ci\detect_secrets_check.py
notepad tools\detect_secrets_findings.json
notepad .secrets.baseline
```

4. To produce a concise human-readable summary, run the parser:

```powershell
python tools\ci\parse_detect_findings.py tools\detect_secrets_findings.json
```

Review and triage
- False positives: if you determine findings are false positives, add them to the baseline (see `detect-secrets` docs) and commit the updated `.secrets.baseline`.
- True positives: rotate keys, revoke tokens, and remove them from history using `git filter-repo` or BFG; re-run the scans locally to confirm the secret is gone before pushing.

Branch protection
- After this workflow has run successfully at least once and you have a trusted baseline, enable branch protection in GitHub to require the `secret-scan` status check before merges.

If you want, I can prepare a draft PR that includes a reviewed `.secrets.baseline` placeholder and a short PR checklist for maintainers to triage initial findings.
