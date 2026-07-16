# Run Security Checks

## Install
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
```

## Unit tests
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Dependency vulnerability scan
```powershell
.\.venv\Scripts\python.exe -m pip_audit -r requirements.txt
```
