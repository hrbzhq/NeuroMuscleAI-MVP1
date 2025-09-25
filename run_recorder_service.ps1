# Simple helper to start the recorder in background using Start-Process
$venv = "$PSScriptRoot\\.venv\\Scripts\\Activate.ps1"
if (Test-Path $venv) {
    & $venv
}
Start-Process -NoNewWindow -FilePath python -ArgumentList '.\\dev_recorder.py -i 30'
Write-Output "Recorder started in background (check dev_session.log)"
