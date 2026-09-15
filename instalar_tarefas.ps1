param(
    [string]$AfternoonTime = "13:30"
)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Exe = Join-Path $ProjectDir "BrasmoAribaMonitorSilent.exe"

if (-not (Test-Path $Exe)) {
    throw "BrasmoAribaMonitorSilent.exe nao encontrado em $ProjectDir"
}

$Action = New-ScheduledTaskAction `
    -Execute $Exe `
    -Argument "run" `
    -WorkingDirectory $ProjectDir

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

$User = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$Principal = New-ScheduledTaskPrincipal `
    -UserId $User `
    -LogonType Interactive `
    -RunLevel Limited

$LogonTrigger = New-ScheduledTaskTrigger -AtLogOn -User $User

Register-ScheduledTask `
    -TaskName "Brasmo - Monitor Ariba - Logon" `
    -Action $Action `
    -Trigger $LogonTrigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Monitor Ariba x SAP ao entrar no Windows." `
    -Force | Out-Null

$At = [DateTime]::Today.Add([TimeSpan]::Parse($AfternoonTime))
$AfternoonTrigger = New-ScheduledTaskTrigger -Daily -At $At

Register-ScheduledTask `
    -TaskName "Brasmo - Monitor Ariba - Tarde" `
    -Action $Action `
    -Trigger $AfternoonTrigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Monitor Ariba x SAP no inicio da tarde." `
    -Force | Out-Null

Write-Host ""
Write-Host "Tarefas criadas/atualizadas:"
Write-Host " - Brasmo - Monitor Ariba - Logon"
Write-Host " - Brasmo - Monitor Ariba - Tarde ($AfternoonTime)"
Write-Host ""
Write-Host "Executavel usado: $Exe"
