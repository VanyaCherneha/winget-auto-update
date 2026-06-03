# Winget Auto-Update for Intune-Managed Windows

Keep third-party apps patched on Windows 10/11 devices by running
`winget upgrade --all` automatically at every user logon — deployed once through
Microsoft Intune, with **no Proactive Remediation license required**.

Outdated software is one of the most common attack surfaces on managed laptops.
This project closes that gap with a tiny, auditable, dependency-free PowerShell
deployment.

---

## Why this exists

Microsoft Intune **Plan 1** (included with Business Premium) has **no Proactive
Remediation**, so you cannot schedule recurring scripts from the cloud. The usual
workaround — paying for an add-on or building a full RMM — is overkill for small
fleets.

Instead, this deploys a **one-time** Intune Platform Script that bootstraps a
**local Scheduled Task**. Intune touches each device once; the device keeps itself
updated from then on.

```
Intune Platform Script (runs once, as SYSTEM)
        │
        ├─ writes  C:\ProgramData\WingetAutoUpdate\Update.ps1
        ├─ writes  C:\ProgramData\WingetAutoUpdate\Launch.vbs
        └─ registers Scheduled Task "WingetAutoUpdate"
                    │
                    └─ at every user logon (+5 min delay)
                            └─ Launch.vbs → powershell → Update.ps1
                                    └─ winget upgrade --all (silent)
```

---

## Features

- **No extra licensing** — works on Intune Plan 1 / Business Premium.
- **Runs in user context** — `winget` resolves from PATH, no SYSTEM workarounds.
- **Fully silent** — VBS launcher prevents the PowerShell console flash that users
  could otherwise close and cancel the update.
- **Network-aware** — waits up to 60s for connectivity before running.
- **Self-verifying install** — reports `Succeeded` to Intune only when the task
  and both scripts actually exist on disk; otherwise `Failed`.
- **Clean reporting** — wraps everything in `try/catch` so stray non-terminating
  errors don't make Intune mark a healthy install as failed.
- **Log rotation** — one timestamped log per run, latest 10 kept.
- **Clean uninstall** — single script removes the task, files, and folder.

---

## Requirements

- Windows 10 (1809+) or Windows 11
- [winget / App Installer](https://learn.microsoft.com/windows/package-manager/winget/)
  present on the device (preinstalled on current Windows 11)
- Devices enrolled in **Microsoft Intune**
- Permission to deploy a Platform Script that runs as **SYSTEM**

---

## Deploy via Intune

1. Go to **Intune admin center → Devices → Scripts and remediations →
   Platform scripts → Add → Windows 10 and later**.
2. Upload [`scripts/Deploy-WingetAutoUpdate.ps1`](scripts/Deploy-WingetAutoUpdate.ps1).
3. Configure:

   | Setting                                   | Value |
   | ----------------------------------------- | ----- |
   | Run this script using the logged-on creds | **No** (run as SYSTEM) |
   | Enforce script signature check            | **No** |
   | Run script in 64-bit PowerShell           | **Yes** |

4. Assign to your device group.

The script runs once per device. After that, the local Scheduled Task takes over
at each logon.

> **Note:** the first upgrade run happens at the next user logon, 5 minutes after
> sign-in (the trigger delay), not immediately at deployment time.

---

## Uninstall

Deploy [`scripts/Uninstall-WingetAutoUpdate.ps1`](scripts/Uninstall-WingetAutoUpdate.ps1)
the same way (Platform Script, as SYSTEM). It unregisters the Scheduled Task and
deletes `C:\ProgramData\WingetAutoUpdate\` with all logs.

---

## How it works

| File on device | Purpose |
| -------------- | ------- |
| `C:\ProgramData\WingetAutoUpdate\Update.ps1` | The actual updater. Runs in user context, calls `winget upgrade --all --silent`. |
| `C:\ProgramData\WingetAutoUpdate\Launch.vbs` | Hidden launcher (window style 0) — starts PowerShell with no visible window. |
| `C:\ProgramData\WingetAutoUpdate\Logs\update_*.log` | One timestamped log per run; oldest pruned beyond 10. |
| Scheduled Task `WingetAutoUpdate` | Trigger: AtLogOn (+5 min). Runs as the `Users` group, RunLevel Limited. |

### Design choices

- **`C:\ProgramData`** — readable/executable by all users, writable by SYSTEM,
  survives profile deletion.
- **Logs ACL** — SYSTEM grants `Users: Modify` on the `Logs` folder so the
  standard-user task can write logs (ProgramData subfolders are read-only for
  Users by default).
- **Limited RunLevel** — no elevation; `winget` works fine in user context.

The full updater logic is embedded as a single-quoted here-string inside
`Deploy-WingetAutoUpdate.ps1` (literal text, written to disk, executed later at
logon) — see the comments in that file.

---

## Run / test locally (without Intune)

You can deploy the whole thing on a single machine to test it before pushing to
Intune. The deploy script does exactly what Intune would do — it just needs an
**elevated** PowerShell (it runs as SYSTEM under Intune; locally you stand in for
SYSTEM with an admin shell).

1. Open **PowerShell as Administrator**.
2. Run the deploy script (bypass execution policy for this one process):

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Deploy-WingetAutoUpdate.ps1
   ```

3. Check the exit code — `0` means install + self-verify passed:

   ```powershell
   $LASTEXITCODE   # 0 = success, 1 = failed
   ```

To remove it again locally, run the uninstall script from an elevated shell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Uninstall-WingetAutoUpdate.ps1
```

---

## Verify it's installed on a device

Run these (no admin needed) to confirm the deployment landed:

```powershell
# 1. Scheduled Task exists?
Get-ScheduledTask -TaskName WingetAutoUpdate

# 2. Scripts on disk?
Test-Path C:\ProgramData\WingetAutoUpdate\Update.ps1
Test-Path C:\ProgramData\WingetAutoUpdate\Launch.vbs

# 3. When did it last run / what was the result?
Get-ScheduledTaskInfo -TaskName WingetAutoUpdate |
    Select-Object LastRunTime, LastTaskResult, NextRunTime
```

`LastTaskResult = 0` means the last run finished cleanly.

---

## Run it now (don't wait for logon)

The task normally fires 5 minutes after logon. To trigger an update immediately:

```powershell
Start-ScheduledTask -TaskName WingetAutoUpdate
```

Then watch the newest log fill up (see below).

---

## Logs

- **Per-run updater output:** `C:\ProgramData\WingetAutoUpdate\Logs\update_*.log`
  (one timestamped file per run, latest 10 kept).
- **Deployment-time messages:** `C:\ProgramData\WingetAutoUpdate\install.log`.

Tail the most recent run live:

```powershell
Get-ChildItem C:\ProgramData\WingetAutoUpdate\Logs\update_*.log |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 |
    Get-Content -Wait -Tail 20
```

---

## Troubleshooting

| Symptom | Likely cause / fix |
| ------- | ------------------ |
| Intune reports **Failed**, exit code 1 | Open `install.log` — the `catch` block logs the exact `ERROR:` and `STACK:`. Usually an ACL or task-registration permission issue. |
| Log says **`winget not found in PATH`** | winget / App Installer missing on the device. Install [App Installer](https://apps.microsoft.com/detail/9nblggh4nns1) (preinstalled on current Win11). winget is per-user, so the task only sees it once the user has it. |
| Task exists but **never runs** | It triggers `AtLogOn` only. Sign out and back in, or run `Start-ScheduledTask -TaskName WingetAutoUpdate` to force it. |
| Updates don't happen at deploy time | By design — the first run is the next logon + 5 min, not deployment time. |
| Log shows a **network/timeout** error | Device had no connectivity in the 60s probe window. It retries at the next logon. |
| Nothing in `Logs\`, access-denied | The `Users: Modify` ACL didn't apply. Re-run the deploy script (it's idempotent) from SYSTEM/admin. |
| A specific app won't upgrade | Run `winget upgrade --all --include-unknown` manually in the user's context to see winget's own error for that package. |
| `running scripts is disabled on this system` | Use `-ExecutionPolicy Bypass` as shown above. Intune already runs scripts with no signature/policy check. |

---

## Security notes

- Scripts run `winget upgrade --all` with `--accept-package-agreements` and
  `--accept-source-agreements`. Review whether auto-accepting EULAs fits your
  policy before deploying fleet-wide.
- The updater only upgrades **already-installed** apps; it does not install new
  software.
- No telemetry, no network calls beyond winget's own source/package traffic and a
  single `8.8.8.8` ping used as a connectivity probe.

---

## Contributing

Issues and PRs welcome. Keep scripts dependency-free and PowerShell 5.1 compatible
(that's what ships in-box on Windows).

---

## License

[MIT](LICENSE)
