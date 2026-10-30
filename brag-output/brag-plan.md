# Brag Plan: Winget Auto-Update

Workflow: `/brag` on Opus 5.5 -> `/brag-slim` (built locally: HTML frames rendered with
headless Chromium, soundtrack synthesized with numpy, muxed with ffmpeg).

## What is it?
A one-time Intune Platform Script that installs a local Scheduled Task, so Windows 10/11
laptops run `winget upgrade --all` silently at every user logon, with no Proactive
Remediation license.

## Who is it for / what does it do for them?
Admins of small Intune fleets on Plan 1 / Business Premium who want third-party apps
patched without paying for an add-on or an RMM.

## What sets it apart?
Intune touches each device once; the device keeps itself updated from then on. Tiny,
auditable, dependency-free PowerShell 5.1.

## The angle
The licensing gap is the villain. "No Proactive Remediation" is the problem slide; the
answer is a deploy-once trick that turns every logon into a patch run. Played straight,
clean, slightly dry: an admin tool that brags by being boring and reliable.

## Hook (0-3s)
"Outdated software" slams in next to a real-looking `winget upgrade` table full of
pending versions, then "= attack surface." lands on the beat.

## Highlights
1. The deployment flow, node by node: Intune Platform Script -> Update.ps1 / Launch.vbs /
   Scheduled Task -> at every logon (+5 min) -> `winget upgrade --all --silent`.
2. The per-run log filling up: source update, upgrades, "Successfully installed".
3. Three feature cards: No extra licensing / Network-aware / Self-verifying install.

## Punchline / outro
"Winget Auto-Update. Patched at every logon." + repo URL + "PowerShell 5.1 · dependency-free · MIT".

## Tone
- Preset: `polished` leaning `default` (the project is a security tool, not a joke)
- Creative direction: calm sysadmin confidence, terminal-native
- Interpretation: few words per scene, long holds, clean dips between scenes; the only
  "joke" is how small the fix is compared to the license it replaces.

## Format: landscape - 1920x1080, 30 fps
## Duration: 22 s (44 beats at 120 BPM)

## Visual identity
The project has no website, so the identity comes from where it lives: the PowerShell 5.1 console.
- Background: `#012456` (classic PowerShell blue), darkened to `#011634` at the edges
- Text: `#EEF3FA`
- Accent: `#3A96DD` (console cyan-blue), success `#16C60C` (console green), alert `#F7768E`
- Display font: Inter Display; body: Inter; code: JetBrains Mono
- Strongest visual element: the README's deployment diagram, rebuilt as animated nodes

## Real material used (all grounded in README / scripts)
- "Outdated software is one of the most common attack surfaces on managed laptops."
- "Intune Plan 1 ... has no Proactive Remediation, so you cannot schedule recurring scripts from the cloud."
- "Intune touches each device once; the device keeps itself updated from then on."
- File names and paths: `C:\ProgramData\WingetAutoUpdate\`, `Update.ps1`, `Launch.vbs`, task `WingetAutoUpdate`, AtLogOn +5 min
- Log section headers from Update.ps1: `=== winget source update ===`, `=== winget upgrade --all ===`
- Features: no extra licensing, fully silent (no console flash), network-aware (waits up to 60s), self-verifying install, latest 10 logs kept
- Illustrative only: the app names/versions in the winget table and log (7-Zip, Firefox,
  Notepad++, VLC) and the log timestamp. No real device, tenant, user or hostname data.

## Share copy (draft)
Intune Plan 1 can't schedule recurring scripts, so I made the laptop do it: one Platform Script, and every logon runs `winget upgrade --all` silently.

## Sound
One piece at 120 BPM in A minor (Am - F - C - G), counted from frame 0; every cut on a beat.
- 0-3s: filtered pluck arpeggio + soft bass pulse, quiet key ticks under the typing
- 3-6s: kick enters, hats, a soft noise riser 4.5-6.0s
- 6s drop: full groove (kick, clap on 2/4, offbeat hats, bass, pad), sidechained
- Nodes/cards: pluck/chime notes from the chord (A, C, E), soft, under the music
- 19.5s: low impact + held Am, drums stop at 21s, ring out and fade by 22s
- Restraint: no harsh highs, repeated ticks stay in the background, one shared reverb space

## Storyboard (cuts on beats)

### Scene 1 - Hook - 0.0-3.0s
Left: "Outdated software" (slam, 0.0s), "= attack surface." (1.5s, alert color).
Right: console window, `PS C:\> winget upgrade` types 0.25-1.0s, 4 table rows tick in on 16ths (texture), "4 upgrades available."
Audio: arp + bass pulse, key ticks, soft hit on 1.5s. Dip to background -> Scene 2.

### Scene 2 - The gap - 3.0-6.0s
Label "Microsoft Intune Plan 1" (3.0s), big "No Proactive Remediation." with a struck badge (3.5s),
sub "Can't schedule recurring scripts from the cloud." (4.0s, holds 1.8s).
Audio: kick enters, riser into the drop. Hard dip -> Scene 3.

### Scene 3 - Reveal - 6.0-9.0s
"Deploy once." (6.0s, drop), "The device keeps itself updated." (7.0s, holds 1.8s), pill `winget-auto-update`.

### Scene 4 - The flow - 9.0-14.0s
Title "Intune touches each device once." Nodes on beats 9.5 / 10.5 / 11.5 / 12.5s with connectors drawing between them:
Intune Platform Script (runs once · as SYSTEM) -> Update.ps1 · Launch.vbs · Scheduled Task (C:\ProgramData\WingetAutoUpdate) -> At every logon (+5 min delay) -> winget upgrade --all (silent · user context).
Audio: one pluck per node.

### Scene 5 - It runs - 14.0-17.0s
Log window `Logs\update_2026-10-30_09-05-12.log` fills line by line (texture); right: "Fully silent." (14.5s) + "No console flash to close." (15.0s).

### Scene 6 - Features - 17.0-19.5s
Three cards on beats 17.0 / 17.5 / 18.0s, then held together: No extra licensing (Intune Plan 1 / Business Premium), Network-aware (waits up to 60s), Self-verifying install (Succeeded only when it's really there).

### Scene 7 - Outro - 19.5-22.0s
"Winget Auto-Update" (19.5s, impact), "Patched at every logon." (20.0s), `github.com/VanyaCherneha/winget-auto-update` + "PowerShell 5.1 · dependency-free · MIT" (20.5s). Hold to the end.
