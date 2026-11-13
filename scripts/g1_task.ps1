# Registers the generation-1 supervisor (scripts/g1_pipeline.py) as a scheduled task that runs whether or not the user is logged on.
# Run ONCE in an elevated PowerShell (Run as administrator):
#     powershell -ExecutionPolicy Bypass -File E:\Moe\eo_hike-1\scripts\g1_task.ps1
# Triggers: at startup, at logon, and every 15 minutes. A second instance exits at once (the supervisor's own lock), so the
# repetition only restarts a supervisor that has died. No time limit; runs on battery too. S4U: no password is stored.
$ErrorActionPreference = "Stop"
$root = "E:\Moe\eo_hike-1"
$user = "$env:USERDOMAIN\$env:USERNAME"
$action = New-ScheduledTaskAction -Execute "$root\.venv-sg\Scripts\python.exe" -Argument "scripts\g1_pipeline.py run" -WorkingDirectory $root
$rep = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 15)
$triggers = @((New-ScheduledTaskTrigger -AtStartup), (New-ScheduledTaskTrigger -AtLogOn -User $user), $rep)
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType S4U -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5)
Register-ScheduledTask -TaskName "eo_hike_g1" -Action $action -Trigger $triggers -Principal $principal -Settings $settings -Force | Out-Null
Get-ScheduledTask -TaskName "eo_hike_g1" | Select-Object TaskName, State, @{n = "Principal"; e = { $_.Principal.LogonType } }
Write-Host "registered. It starts by itself within a minute (or: Start-ScheduledTask -TaskName eo_hike_g1)."
