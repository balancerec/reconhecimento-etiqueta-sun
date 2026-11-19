param([ValidateSet('Start','Stop','Logs','Test')][string]$Action='Start')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'common.ps1')
try {
    $docker=Get-LabelsDocker
    if($Action -eq 'Stop'){
        Invoke-LabelsCompose $docker $root @('stop')
        Write-Host 'Etiquetas parado. Fotos e historico preservados.'
    } elseif($Action -eq 'Logs'){
        Invoke-LabelsCompose $docker $root @('ps')
        Invoke-LabelsCompose $docker $root @('logs','--tail','150')
        Read-Host 'Enter para fechar' | Out-Null
    } else {
        Wait-LabelsDocker $docker
        Invoke-LabelsCompose $docker $root @('up','-d','--no-build')
        $port=Get-LabelsPort $root;Wait-LabelsApi $port
        if($Action -eq 'Test'){& (Join-Path $PSScriptRoot 'test-labels.ps1') -Port $port}
        else{Start-Process ('http://localhost:{0}/?local=1' -f $port)}
    }
} catch {Write-Host $_ -ForegroundColor Red;Read-Host 'Enter para fechar' | Out-Null;exit 1}
