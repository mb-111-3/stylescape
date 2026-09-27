$ErrorActionPreference = "Stop"
# The app loads .env; configure or replace the key at /admin/ after startup.
& "$PSScriptRoot\venv\Scripts\python.exe" "$PSScriptRoot\app.py"
