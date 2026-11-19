Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
function Get-LabelsDocker {
    $candidates=@(
        (Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\resources\bin\docker.exe'),
        (Join-Path $env:ProgramFiles 'Docker\Docker\resources\bin\docker.exe')
    )
    $command=Get-Command docker.exe -ErrorAction SilentlyContinue
    if($command){$candidates+= $command.Source}
    foreach($candidate in $candidates){if(Test-Path -LiteralPath $candidate -PathType Leaf){return $candidate}}
    throw 'Docker CLI nao encontrado. Instale ou repare o Docker Desktop e tente novamente.'
}
function Get-LabelsEngine([string]$Docker) {
    $saved=$ErrorActionPreference
    try {
        $ErrorActionPreference='Continue'
        $engine=& $Docker info --format '{{.OSType}}' 2>$null
        if($LASTEXITCODE -eq 0){return ($engine | Select-Object -Last 1)}
        return ''
    } finally {$ErrorActionPreference=$saved}
}
function Wait-LabelsDocker([string]$Docker) {
    $engine=Get-LabelsEngine $Docker
    if(-not $engine){
        $desktop=@(
            (Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\Docker Desktop.exe'),
            (Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe')
        ) | Where-Object {Test-Path -LiteralPath $_ -PathType Leaf} | Select-Object -First 1
        if($desktop){Write-Host 'Iniciando Docker Desktop...';Start-Process -FilePath $desktop -WindowStyle Hidden}
        $limit=(Get-Date).AddMinutes(4)
        do {
            Start-Sleep -Seconds 3
            $engine=Get-LabelsEngine $Docker
            if($engine){break}
            Write-Host 'Aguardando o motor Docker...'
        } while((Get-Date) -lt $limit)
    }
    if(-not $engine){throw 'Sem acesso ao motor Docker. Abra o Docker Desktop nesta conta do Windows e execute novamente. Nenhuma reinstalacao do Ubuntu e necessaria.'}
    if($engine -ne 'linux'){throw 'Selecione Linux containers no Docker Desktop e tente novamente.'}
    & $Docker compose version | Out-Null
    if($LASTEXITCODE -ne 0){throw 'Docker Compose v2 indisponivel. Atualize o Docker Desktop.'}
}
function Invoke-LabelsCompose([string]$Docker,[string]$Root,[string[]]$ComposeArgs) {
    & $Docker compose --project-name proact-etiquetas --project-directory $Root --file (Join-Path $Root 'compose.yaml') @ComposeArgs
    if($LASTEXITCODE -ne 0){throw ('Docker Compose falhou: '+($ComposeArgs -join ' '))}
}
function Get-LabelsPort([string]$Root) {
    $config=Join-Path $Root '.env'
    if(Test-Path -LiteralPath $config){
        $line=Get-Content -LiteralPath $config | Where-Object {$_ -match '^LABEL_PORT=(\d+)$'} | Select-Object -First 1
        if($line -and $line -match '^LABEL_PORT=(\d+)$'){
            $port=[int]$Matches[1];if($port -ge 1024 -and $port -le 65535){return $port}
        }
    }
    return 8000
}
function Wait-LabelsApi([int]$Port) {
    $limit=(Get-Date).AddMinutes(5)
    do {
        try {
            $status=Invoke-RestMethod -Uri ('http://localhost:{0}/health' -f $Port) -TimeoutSec 30
            if($status.status -eq 'ok' -and $status.version -eq '0.2.0' -and $status.engines.rapidocr -eq $true){return}
        } catch {}
        Write-Host 'Preparando Tesseract e RapidOCR...';Start-Sleep -Seconds 3
    } while((Get-Date) -lt $limit)
    throw 'O servico nao ficou saudavel. Use o atalho Diagnostico para consultar os logs. Seus dados foram preservados.'
}
