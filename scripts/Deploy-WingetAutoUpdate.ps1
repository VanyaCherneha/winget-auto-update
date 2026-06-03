# =============================================================================
# WingetAutoUpdate for Microsoft Business Premium
# =============================================================================
# Deployed ONCE via Intune Platform Script (runs as SYSTEM). It does not update
# apps itself -- instead it:
#   1) Drops a second script (Update.ps1) into C:\ProgramData\WingetAutoUpdate\
#   2) Registers a Scheduled Task that runs Update.ps1 at every user logon
#
# Why this approach: Business Premium has no Proactive Remediation, so we can't
# schedule recurring scripts through Intune. A local Scheduled Task is the
# workaround.
#
# Reporting model:
#   - Any non-terminating error from a cmdlet (e.g. Set-Acl, Register-ScheduledTask)
#     leaks to the PowerShell error stream and Intune reports the script as
#     "Failed" even when exit code is 0.
#   - To fix this we wrap everything in try/catch with ErrorActionPreference=Stop,
#     and we verify the real outcome at the end (task exists + files exist).
#     Exit 0 ONLY when the verification passes. Exit 1 otherwise.
# =============================================================================

$ErrorActionPreference = 'Stop'

# Task name in Task Scheduler and paths for the child script
$taskName    = "WingetAutoUpdate"
$scriptDir   = "$env:ProgramData\WingetAutoUpdate"
$scriptPath  = "$scriptDir\Update.ps1"
$vbsPath     = "$scriptDir\Launch.vbs"
$installLog  = "$scriptDir\install.log"

# Local helper to record progress to install.log without touching the error stream.
function Write-InstallLog {
    param([string]$Message)
    $line = "{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    try { Add-Content -Path $installLog -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue } catch { }
}

try {

    # --- STEP 1: Create Update.ps1 in ProgramData --------------------------------
    # ProgramData is chosen because:
    #   - readable/executable by all users
    #   - SYSTEM can write there (the Intune script runs as SYSTEM)
    #   - survives user profile deletions

    if (-not (Test-Path $scriptDir)) {
        New-Item -ItemType Directory -Path $scriptDir -Force | Out-Null
    }
    Write-InstallLog "scriptDir ready: $scriptDir"

    # Create the Logs subfolder and grant Users write access while running as SYSTEM.
    # By default ProgramData subfolders inherit Read-only for Users, so without this
    # Update.ps1 (running as a standard user) would get Access Denied writing logs.
    $logDir = "$scriptDir\Logs"
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }

    $acl  = Get-Acl $logDir
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        "BUILTIN\Users", "Modify", "ContainerInherit,ObjectInherit", "None", "Allow")
    $acl.AddAccessRule($rule)
    Set-Acl -Path $logDir -AclObject $acl
    Write-InstallLog "ACL set on $logDir"

    # @'...'@ is a single-quoted here-string. Everything between the markers is
    # written to Update.ps1 AS LITERAL TEXT -- no variable expansion, no execution.
    # The code below will run later, at user logon, from the file on disk.
    @'
# --- Update.ps1 ---------------------------------------------------------------
# Triggered by the Scheduled Task at every user logon.
# Runs in user context (not SYSTEM), so winget is available via PATH.

# Fix encoding so winget's Unicode progress output is captured correctly.
# Without this, PowerShell 5.1 uses the system code page (e.g. Windows-1252)
# and winget's box-drawing characters appear as garbled text in the log.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding             = [System.Text.Encoding]::UTF8

# Prepare log folder and a timestamped filename (one log per run)
$logDir  = "$env:ProgramData\WingetAutoUpdate\Logs"
$logFile = "$logDir\update_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').log"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

# Wait up to 60s for the network to come up.
# At logon the network is often not ready yet -- Wi-Fi not connected, VPN not up.
# Without this wait, winget can fail with a "no network" error.
$deadline = (Get-Date).AddSeconds(60)
while ((Get-Date) -lt $deadline -and -not (Test-Connection -ComputerName 8.8.8.8 -Count 1 -Quiet)) {
    Start-Sleep -Seconds 5
}

# Verify winget is installed on this machine
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    "winget not found in PATH" | Out-File $logFile -Encoding utf8
    exit 1
}

# Refresh the package catalogs (winget sources).
# Without this winget will use a stale cache and may miss new versions.
"=== winget source update ===" | Out-File $logFile -Encoding utf8
winget source update --disable-interactivity 2>&1 | Out-File $logFile -Encoding utf8 -Append

# Main command -- upgrade ALL installed applications.
#   --all                          upgrade everything, no prompts
#   --include-unknown              include apps whose versions winget doesn't know
#   --accept-package-agreements    auto-accept each package's EULA
#   --accept-source-agreements     auto-accept source terms
"`n=== winget upgrade --all ===" | Out-File $logFile -Encoding utf8 -Append
winget upgrade --all --include-unknown --silent --accept-package-agreements --accept-source-agreements --disable-interactivity 2>&1 |
    Out-File $logFile -Encoding utf8 -Append

# Trim old logs -- keep only the latest 10 so the folder doesn't grow forever
Get-ChildItem $logDir -Filter "update_*.log" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip 10 |
    Remove-Item -Force -ErrorAction SilentlyContinue
'@ | Set-Content -Path $scriptPath -Encoding UTF8
    Write-InstallLog "Update.ps1 written"

    # Create a VBS launcher that starts PowerShell with zero visible windows.
    # PowerShell's -WindowStyle Hidden has a known issue: the console window briefly
    # flashes before hiding. If the user sees it and closes it, the script is killed.
    # WScript.Shell.Run with window style 0 avoids this entirely -- no window at all.
    @"
Set objShell = CreateObject("WScript.Shell")
objShell.Run "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""$scriptPath""", 0, True
"@ | Set-Content -Path $vbsPath -Encoding ASCII
    Write-InstallLog "Launch.vbs written"


    # --- STEP 2: Describe the Scheduled Task --------------------------------------

    # ACTION -- run the VBS launcher instead of PowerShell directly.
    # wscript.exe does not create a console window, so the user sees nothing.
    $action = New-ScheduledTaskAction `
        -Execute   "wscript.exe" `
        -Argument  "`"$vbsPath`""

    # TRIGGER -- when to fire. AtLogOn = on every user logon.
    # 5-minute delay so the task doesn't compete with other logon-time processes.
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $trigger.Delay = "PT5M"

    # PRINCIPAL -- who the task runs as.
    # S-1-5-32-545 is the SID of the built-in "Users" group, so the task runs as
    # whichever user just logged on.
    # RunLevel Limited -- no admin elevation (standard user).
    # This matters: winget works in user context; running as SYSTEM needs workarounds.
    $principal = New-ScheduledTaskPrincipal `
        -GroupId   "S-1-5-32-545" `
        -RunLevel  Limited

    # SETTINGS -- additional task options
    #   -ExecutionTimeLimit       max 1 hour to run (then the task is killed)
    #   -MultipleInstances        if already running -- don't spawn duplicates
    #   -StartWhenAvailable       if the device was off at trigger time -- run when back on
    #   -AllowStartIfOnBatteries  run even when the laptop is on battery (most BP devices are laptops)
    #   -DontStopIfGoingOnBatteries  don't kill the task if user unplugs during update
    $settings = New-ScheduledTaskSettingsSet `
        -ExecutionTimeLimit          (New-TimeSpan -Hours 1) `
        -MultipleInstances           IgnoreNew `
        -StartWhenAvailable `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries


    # --- STEP 3: Register the task in the system ----------------------------------
    # -Force overwrites any existing task with the same name -- useful when this
    # script is re-deployed (e.g., after the script itself is updated).
    # If a stale task exists from manual testing, Register-ScheduledTask -Force
    # would still emit a warning to the error stream. Remove first to keep clean.
    if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-InstallLog "Existing task removed before re-register"
    }

    Register-ScheduledTask `
        -TaskName    $taskName `
        -Description "Updates installed applications via winget on user logon" `
        -Action      $action `
        -Trigger     $trigger `
        -Principal   $principal `
        -Settings    $settings | Out-Null
    Write-InstallLog "Scheduled task registered"


    # --- STEP 4: Verify the install actually worked -------------------------------
    # We only report Succeeded to Intune if all three of these are true:
    #   1) Update.ps1 exists on disk
    #   2) Launch.vbs exists on disk
    #   3) The Scheduled Task is registered

    $okScript = Test-Path $scriptPath
    $okVbs    = Test-Path $vbsPath
    $okTask   = [bool](Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue)

    if (-not ($okScript -and $okVbs -and $okTask)) {
        Write-InstallLog "VERIFY FAIL: scriptPath=$okScript vbsPath=$okVbs task=$okTask"
        # Throw to fall into catch and exit 1 -- this is a real failure.
        throw "Verification failed: Update.ps1=$okScript Launch.vbs=$okVbs Task=$okTask"
    }

    Write-InstallLog "VERIFY OK -- exit 0"

    # Clear any non-terminating errors that may have been silently collected
    # during the run, so Intune doesn't pick them up from the error stream.
    $Error.Clear()

    exit 0
}
catch {
    # Real failure path: log the error and exit non-zero so Intune reports Failed.
    Write-InstallLog "ERROR: $($_.Exception.Message)"
    Write-InstallLog "STACK: $($_.ScriptStackTrace)"
    exit 1
}
