param([string]$SourcePath=(Split-Path -Parent $PSScriptRoot),[string]$InstallDir=(Join-Path $env:LOCALAPPDATA 'PROACT\Etiquetas'))
$ErrorActionPreference='Stop'
try {
    Write-Host 'PRO-ACT Etiquetas - Instalador local 0.2.0' -ForegroundColor Cyan
    Write-Host 'Instalacao por usuario. Fotos e historico existentes serao preservados.'
    $source=[IO.Path]::GetFullPath($SourcePath)
    $target=[IO.Path]::GetFullPath($InstallDir)
    if($target -eq [IO.Path]::GetPathRoot($target)){throw 'Diretorio de instalacao invalido'}
    New-Item -ItemType Directory -Path $target -Force | Out-Null
    $manifest=Get-Content -Raw -LiteralPath (Join-Path $source 'package-manifest.json') | ConvertFrom-Json
    foreach($relative in $manifest.files){
        $from=[IO.Path]::GetFullPath((Join-Path $source $relative));$to=[IO.Path]::GetFullPath((Join-Path $target $relative))
        if(-not $from.StartsWith($source.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase) -or -not $to.StartsWith($target.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Caminho fora do pacote'}
        New-Item -ItemType Directory -Path (Split-Path -Parent $to) -Force | Out-Null
        if($from -ne $to){Copy-Item -LiteralPath $from -Destination $to -Force}
    }
    $logs=Join-Path $target 'logs';New-Item -ItemType Directory -Path $logs -Force | Out-Null
    Start-Transcript -LiteralPath (Join-Path $logs ('install-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')) | Out-Null
    . (Join-Path $target 'windows\common.ps1')
    $docker=Get-LabelsDocker;Write-Host ('Docker encontrado: '+$docker);Wait-LabelsDocker $docker
    if(-not(Test-Path -LiteralPath (Join-Path $target '.env'))){
        $chosen=$null
        foreach($candidate in @(8000,8010,8020,8030)){
            $listener=New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback,$candidate)
            try{$listener.Start();$chosen=$candidate;break}catch{}finally{$listener.Stop()}
        }
        if(-not $chosen){throw 'Portas 8000, 8010, 8020 e 8030 ocupadas. Libere uma delas.'}
        ('LABEL_PORT='+$chosen) | Set-Content -Encoding ASCII -LiteralPath (Join-Path $target '.env')
    }
    $shell=New-Object -ComObject WScript.Shell
    $destinations=@([Environment]::GetFolderPath('Desktop'),(Join-Path ([Environment]::GetFolderPath('Programs')) 'PROACT Etiquetas'))
    foreach($folder in $destinations){
        New-Item -ItemType Directory -Path $folder -Force | Out-Null
        foreach($entry in @(@('Abrir Etiquetas','Start'),@('Parar Etiquetas','Stop'),@('Diagnostico Etiquetas','Logs'),@('Testar Etiquetas','Test'))){
            $shortcut=$shell.CreateShortcut((Join-Path $folder ($entry[0]+'.lnk')))
            $shortcut.TargetPath=Join-Path $PSHOME 'powershell.exe'
            $shortcut.Arguments='-NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $target 'windows\runtime.ps1')+'" -Action '+$entry[1]
            $shortcut.WorkingDirectory=$target;$shortcut.Save()
        }
    }
    Write-Host 'Baixando dependencias e preparando os dois motores. A primeira instalacao precisa de internet e pode levar alguns minutos.'
    Invoke-LabelsCompose $docker $target @('build','--pull')
    Invoke-LabelsCompose $docker $target @('up','-d','--no-build')
    $port=Get-LabelsPort $target;Wait-LabelsApi $port
    Stop-Transcript | Out-Null
    Write-Host ('Pronto. Instalado em '+$target) -ForegroundColor Green
    Start-Process ('http://localhost:{0}/?local=1' -f $port)
} catch {
    Write-Host ('Falha: '+$_) -ForegroundColor Red
    try{Stop-Transcript | Out-Null}catch{}
    Read-Host 'Enter para fechar' | Out-Null
    exit 1
}
