# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-03

### Added
- `Deploy-WingetAutoUpdate.ps1` — Intune Platform Script that installs a local
  Scheduled Task running `winget upgrade --all` at every user logon.
- `Uninstall-WingetAutoUpdate.ps1` — removes the Scheduled Task, scripts, and logs.
- Hidden execution via a VBS launcher (no console window flash).
- Network-readiness wait loop (up to 60s) before running winget.
- Self-verifying install: exit 0 only when the task and both files exist.
- Per-run timestamped logs with automatic retention (latest 10 kept).
