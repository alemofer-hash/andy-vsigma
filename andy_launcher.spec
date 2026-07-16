# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


hiddenimports = sorted(
    set(
        collect_submodules("streamlit")
        + collect_submodules("pandas")
        + collect_submodules("pyarrow")
        + collect_submodules("openpyxl")
        + collect_submodules("desktop_app")
        + collect_submodules("andy_threads")
        + [
            "andys_table_app",
            "andys_report_runner",
            "andys_indexer",
            "config",
            "runtime_paths",
            "andy_version",
            "db.query_builder",
            "utils.parsing",
            "utils.formatting",
            "security.auth",
            "security.audit",
            "security.errors",
            "audit.export_auditor",
            "xlsx_selection",
            "measurement_value",
        ]
    )
)

datas = collect_data_files("streamlit")
datas += [
    ("andys_table_app.py", "."),
    ("README.md", "."),
]


a = Analysis(
    ["launch_andy.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Sentinela",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Sentinela",
)
