param([string]$ProjectRoot=(Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($ProjectRoot)
$files=@('index.html','backend-client.js','compose.yaml','.dockerignore','README.md','Instalar.cmd','windows\install.ps1','windows\common.ps1','windows\runtime.ps1','windows\test-labels.ps1','docs\etiquetas-dun-sun.svg')
$files+=Get-ChildItem -LiteralPath (Join-Path $root 'backend') -Recurse -File | Where-Object {$_.Extension -in '.py','.txt','.md' -or $_.Name -eq 'Dockerfile'} | ForEach-Object {$_.FullName.Substring($root.Length+1)}
$manifest=@{version='0.2.0';files=$files}
$manifest.files+= 'package-manifest.json'
$manifest | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $root 'package-manifest.json')
$stage=Join-Path $env:TEMP ('proact-package-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage -Force | Out-Null
foreach($name in $manifest.files){
    $target=Join-Path $stage $name
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    Copy-Item -LiteralPath (Join-Path $root $name) -Destination $target
}
$output=Join-Path $root 'downloads';New-Item -ItemType Directory -Force -Path $output | Out-Null
$zip=Join-Path $output 'Etiquetas-Windows.zip'
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip -Force
$csc=Join-Path ([Runtime.InteropServices.RuntimeEnvironment]::GetRuntimeDirectory()) 'csc.exe'
if(-not(Test-Path -LiteralPath $csc)){$csc=Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'}
$exe=Join-Path $output 'Instalar-Etiquetas.exe'
& $csc /nologo /target:exe /platform:anycpu /reference:System.IO.Compression.dll /reference:System.IO.Compression.FileSystem.dll ('/resource:'+$zip+',payload.zip') ('/out:'+$exe) (Join-Path $root 'windows\Installer.cs')
if($LASTEXITCODE -ne 0){throw 'Falha ao compilar instalador'}
Get-FileHash -Algorithm SHA256 -LiteralPath $exe
Write-Host ('Instalador criado: '+$exe)
