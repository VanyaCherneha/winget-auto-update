# =============================================================================
# WingetAutoUpdate -- UNINSTALL
# =============================================================================
# Deploy via Intune Platform Script to remove WingetAutoUpdate from all devices.
# Runs as SYSTEM. Removes the Scheduled Task, all files, and the folder.
# =============================================================================

$taskName  = "WingetAutoUpdate"
$scriptDir = "$env:ProgramData\WingetAutoUpdate"

# Remove the Scheduled Task (if it exists)
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Remove the folder with all files and logs
if (Test-Path $scriptDir) {
    Remove-Item $scriptDir -Recurse -Force
}

exit 0
