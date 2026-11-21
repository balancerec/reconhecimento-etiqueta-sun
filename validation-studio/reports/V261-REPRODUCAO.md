# Reproduction

From PowerShell:

```powershell
& "$env:TEMP\sun-v26-studio-20261120-01\scripts\Start-Studio.ps1"
```

API smoke/integration checks: run `scripts/test_v261_final.py` from the project root with `.venv-api` and `PYTHONPATH` set to the project root. OpenCV worker uses `o Python GPU configurado em `vision/api/app.py` (ajuste esse caminho para a m?quina local)`.

