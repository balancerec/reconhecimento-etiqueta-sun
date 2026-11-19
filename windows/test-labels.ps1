param([int]$Port=8000,[string]$ImagesDir=(Join-Path $env:USERPROFILE 'Pictures\ETIQUETAS'))
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$reportDir=Join-Path $root ('reports\'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
$images=@(Get-ChildItem -LiteralPath $ImagesDir -File -ErrorAction SilentlyContinue | Where-Object {$_.Extension -match '^\.(jpg|jpeg|png)$'})
$archive=Join-Path $ImagesDir 'ETIQUETAS.rar'
if($images.Count -eq 0 -and (Test-Path -LiteralPath $archive)){
    $fixtures=Join-Path $reportDir 'amostras'
    New-Item -ItemType Directory -Path $fixtures -Force | Out-Null
    # Extract the known archive into a new reports subdirectory, preserving originals.
    & tar.exe -xf $archive -C $fixtures
    if($LASTEXITCODE -ne 0){throw 'Nao foi possivel extrair ETIQUETAS.rar'}
    $images=@(Get-ChildItem -LiteralPath $fixtures -File | Where-Object {$_.Extension -match '^\.(jpg|jpeg|png)$'})
}
if($images.Count -eq 0){throw ('Nenhuma imagem encontrada em '+$ImagesDir)}
$summary=@()
foreach($image in $images){
    Write-Host ('Lendo '+$image.Name+'...')
    $output=Join-Path $reportDir ($image.BaseName+'.json')
    & curl.exe --silent --show-error --fail-with-body --max-time 300 --output $output --form ('image=@'+$image.FullName) ('http://localhost:{0}/v1/recognize' -f $Port)
    if($LASTEXITCODE -ne 0){$summary+=[pscustomobject]@{Arquivo=$image.Name;Resultado='Falha HTTP';Tipo='';SKU='';Avisos='Consulte o JSON e os logs'};continue}
    $result=Get-Content -Raw -LiteralPath $output | ConvertFrom-Json
    foreach($label in $result.labels){
        $summary+=[pscustomobject]@{Arquivo=$image.Name;Resultado=$label.validation.status;Tipo=$label.label_type;SKU=$label.fields.sku;Avisos=($label.validation.warnings -join ', ')}
    }
}
$summary | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $reportDir 'resumo.json')
$summary | ConvertTo-Html -Title 'Teste local de etiquetas' -PreContent '<h1>Resultados locais</h1><p>Conferir contra as fotos. Campos reconhecidos nao equivalem a acuracia comprovada.</p>' | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $reportDir 'resumo.html')
Start-Process (Join-Path $reportDir 'resumo.html')
Write-Host ('Relatorios em '+$reportDir)
Read-Host 'Enter para fechar' | Out-Null
