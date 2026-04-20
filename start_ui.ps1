param([int]$Port = 8471)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
& "$PSScriptRoot\venv\Scripts\Activate.ps1"
python -m uvicorn ui.main_ui:app --reload --port $Port
