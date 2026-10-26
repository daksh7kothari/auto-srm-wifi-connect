$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = (Get-Command python.exe -ErrorAction Stop).Source }
& $python -c 'import login; login.credentials()'
if ($LASTEXITCODE -ne 0) { throw 'Fill .env before installing the task.' }

$action = New-ScheduledTaskAction -Execute $python -Argument ('"{0}"' -f (Join-Path $PSScriptRoot 'login.py')) -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName 'SRM WiFi Monitor' -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Unregister-ScheduledTask -TaskName 'SRM WiFi Auto Login' -Confirm:$false -ErrorAction SilentlyContinue
Start-ScheduledTask -TaskName 'SRM WiFi Monitor'
Write-Host 'SRM WiFi Monitor installed and started. It will start again at Windows sign-in.'
