# ANDY Desktop Operational Baseline

Status: preserve_baseline_documented

Scope: ANDY real desktop baseline before sanitize/refactor work.

## Summary

The current functional ANDY baseline is a Python desktop/data product with a native PySide6 interface, local DuckDB/Parquet runtime, PyInstaller packaging, and Inno Setup installer/update flow.

This baseline must be preserved before any Git safety, sanitization, packaging cleanup, runtime relocation, remote setup, workspace discovery, Snowflake adapter, or homologation work.

## Functional Desktop Version

Detected operational identity:
- Product name: `Andy vSigma`.
- Version: `1.2.3`.
- Build profile: `full`.
- Current packaged executable: `dist/ANDY/Andy vSigma.exe`.
- Current packaged build metadata: `dist/ANDY/BUILD_INFO.txt`, `dist/ANDY/PROFILE.txt`, `dist/ANDY/VERSION.txt`.

The app should continue to work both as source desktop and packaged desktop.

## Main Entrypoint

Primary entrypoint:
- `desktop_andy.py`

Expected responsibilities:
- set Windows AppUserModelID;
- load `desktop_app.main_window`;
- surface early startup failures with a user-readable log path;
- keep startup failure logs under the user-local ANDY runtime, not inside source data.

Expected source launch command:

```powershell
python desktop_andy.py
```

Expected packaged launch target:

```powershell
dist\ANDY\Andy vSigma.exe
```

Helper script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_packaged_local.ps1
```

## Main UI

Primary UI package:
- `desktop_app/`

Core UI/service files:
- `desktop_app/main_window.py`
- `desktop_app/runtime.py`
- `desktop_app/query_service.py`
- `desktop_app/export_service.py`
- `desktop_app/models.py`
- `desktop_app/theme.py`
- `desktop_app/splash.py`
- `desktop_app/app_icon.py`

Baseline expectation:
- `desktop_app/` remains the primary installed desktop UI.
- PySide6/Qt remains the installed desktop framework.
- Streamlit must not replace the PySide6 baseline.
- Electron must not be introduced as a required dependency for this baseline.

## Auxiliary Tools

The following tools are part of the operational surface and must remain discoverable:
- `andys_indexer.py`: builds local Parquet lake and DuckDB catalog from source spreadsheets.
- `andys_report_runner.py`: generates XLSX reports from the lake.
- `andys_viewer.py`: CLI viewer/query helper for DuckDB/Parquet.
- `runtime_paths.py`: user-local runtime path resolution.
- `runtime_bootstrap.py`: local DB bootstrap/reuse/repair.
- `runtime_metadata.py`: runtime state, catalog inspection and repair.
- `shared_catalog.py`: shared snapshot publish/sync support.

## Streamlit / Dev UI

Legacy/dev UI:
- `andys_table_app.py`
- `launch_andy.py`

Baseline expectation:
- Streamlit remains documented as engineering/dev support.
- Streamlit is not the primary installed desktop surface.
- Future cleanup must not silently remove this surface before replacement/retirement is explicitly approved.

## Runtime Root

Installed/default runtime root:

```text
%LOCALAPPDATA%\ANDY
```

Expected runtime subtrees:

```text
%LOCALAPPDATA%\ANDY\config
%LOCALAPPDATA%\ANDY\workspace
%LOCALAPPDATA%\ANDY\workspace\ANDYS_LAKE
%LOCALAPPDATA%\ANDY\workspace\ANDYS_EXPORTS
%LOCALAPPDATA%\ANDY\logs
%LOCALAPPDATA%\ANDY\cache
%LOCALAPPDATA%\ANDY\updates
%LOCALAPPDATA%\ANDY\updates\rollback
```

Important runtime files:
- `config/settings.json`
- `config/domain_profile.json`
- `config/runtime_state.json`
- `config/install_state.json`
- `config/rollback_state.json`
- `workspace/ANDYS_LAKE/andys.duckdb`
- `workspace/ANDYS_LAKE/manifest.json`
- `logs/app_error.log`
- `logs/desktop_app.log`
- `logs/audit.jsonl`
- `updates/update_history.jsonl`

## Local Data Engine

Data engine:
- DuckDB local catalog.
- Parquet lake.

Expected lake shape:

```text
ANDYS_LAKE/
  andys.duckdb
  manifest.json
  ano=YYYY/mes=MM/medicoes_*.parquet
  canonico/ano=YYYY/mes=MM/medicoes_canon_*.parquet
```

Compatibility expectation:
- Existing local DuckDB/Parquet lake layouts must keep opening.
- Repair/reuse behavior must remain conservative.
- Full reindex from source should remain an explicit fallback, not a silent first choice when local lake is usable.

## Build Baseline

Packaging:
- PyInstaller via `andy_launcher.spec`.

Build helper:
- `scripts/build_exe.ps1`

Baseline expectation:
- Future packaging changes must keep `desktop_andy.py` as the packaged entrypoint.
- Future packaging changes must preserve PySide6, DuckDB, pandas, pyarrow and openpyxl runtime availability.
- Future packaging changes must keep domain profiles and docs bundled where currently expected.

## Installer / Update Baseline

Installer/update:
- Inno Setup via `installer/ANDY.iss`.

Helper scripts:
- `scripts/build_installer.ps1`
- `scripts/build_update.ps1`
- `scripts/assert_inno_setup_safety.ps1`
- `scripts/verify_packaged_runtime.ps1`

Observed current artifacts:
- `artifacts/installer/Andy vSigma-Setup-1.2.3.exe`
- `artifacts/updates/Andy vSigma-Update-1.2.3.exe`

Baseline expectation:
- Installer/update scripts remain traceable.
- Existing generated artifacts are treated as generated outputs until classified.
- Update must preserve `%LOCALAPPDATA%\ANDY` user runtime.
- Rollback metadata and existing update history remain part of the compatibility surface.

## Required Configuration

Core project config:
- `requirements.txt`
- `requirements-dev.txt`
- `config.py`
- `config/domains/rs.default.json`
- `config/domains/pa.pilot.json`
- `config/domains/generic.default.json`
- `configs/security_protocol.json`

Runtime/domain selection:
- `RS` profile can use the configured corporate source when available.
- `PA` and `GENERIC` require manual source selection.
- Domain profile configuration persists under `%LOCALAPPDATA%\ANDY\config\domain_profile.json`.

## Must Not Break

Preserve these behaviors:
- `desktop_andy.py` remains the source desktop entrypoint.
- `desktop_app/` remains the primary installed UI.
- `dist/ANDY/Andy vSigma.exe` remains the current packaged baseline artifact until a new build is explicitly approved.
- `%LOCALAPPDATA%\ANDY` remains the user-local runtime root.
- Existing DuckDB/Parquet lake layout remains compatible.
- Installer/update metadata remains traceable.
- CLI tools remain localizable.
- Streamlit dev UI remains documented.
- Source roots stay read-only.
- Exports/logs/cache/runtime outputs stay outside source roots.
- Electron, Snowflake, remote publication and workspace discovery are not required for this baseline.

## Preservation Rule

Any future change that touches desktop startup, runtime paths, DuckDB/Parquet, packaging, installer/update, export behavior, or source-root resolution must either preserve this baseline or explicitly declare a blocking compatibility risk before proceeding.
