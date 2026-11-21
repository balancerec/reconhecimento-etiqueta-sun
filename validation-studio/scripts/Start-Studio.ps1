param([int]$Port=8000)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$base="http://127.0.0.1:$Port"
try {
  $session=Invoke-RestMethod -Uri "$base/api/session" -TimeoutSec 2
  if ($session.photo_count -ge 1) {
    Write-Host "Validation Studio já está ativo em $base/ ($($session.photo_count) fotografias). Reutilizando a instância existente."
    return
  }
} catch { }
$listener=netstat -ano | Select-String ":$Port\s+.*LISTENING"
if ($listener) {
  throw "A porta $Port já está ocupada por outro processo e não respondeu como Validation Studio. Não encerrei o processo. Use -Port 8001 ou libere a porta manualmente."
}
& "$root\.venv-api\Scripts\python.exe" -m uvicorn vision.api.app:app --app-dir $root --host 127.0.0.1 --port $Port

