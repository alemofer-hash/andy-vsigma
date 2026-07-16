from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


MIN_TLS_VERSION = "1.2"
FORBIDDEN_SECRET_KEYS = {
    "password",
    "passwd",
    "pwd",
    "secret",
    "client_secret",
    "token",
    "refresh_token",
    "private_key",
    "certificate_private_key",
}
HTTPS_FIELDS = {
    "authority_url",
    "metadata_url",
    "jwks_url",
    "issuer_url",
    "audit_sink_url",
    "source_catalog_url",
}
LOCAL_HTTP_FIELDS = {"redirect_uri"}
LDAPS_FIELDS = {"server_url", "ldap_url"}


@dataclass(frozen=True)
class HttpsFinding:
    code: str
    severity: str
    field_path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "field_path": self.field_path,
            "message": self.message,
        }


@dataclass(frozen=True)
class HttpsSecurityReport:
    status: str
    findings: tuple[HttpsFinding, ...] = field(default_factory=tuple)
    endpoints: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    safety_boundary: dict[str, bool] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "findings": [item.as_dict() for item in self.findings],
            "endpoints": list(self.endpoints),
            "safety_boundary": dict(self.safety_boundary),
        }


def validate_https_security_config(config: dict[str, Any]) -> HttpsSecurityReport:
    findings: list[HttpsFinding] = []
    endpoints: list[dict[str, Any]] = []
    _walk(config, "", findings, endpoints)
    tls = config.get("https_security", {})
    if isinstance(tls, dict):
        if tls.get("verify_tls_certificates") is not True:
            findings.append(_finding("tls_certificate_verification_required", "ERROR", "https_security.verify_tls_certificates"))
        if tls.get("allow_self_signed_certificates") is True:
            findings.append(_finding("self_signed_certificates_not_allowed", "ERROR", "https_security.allow_self_signed_certificates"))
        if str(tls.get("min_tls_version", "")).strip() not in {"1.2", "1.3"}:
            findings.append(_finding("min_tls_version_required", "ERROR", "https_security.min_tls_version"))
    else:
        findings.append(_finding("https_security_required", "ERROR", "https_security"))
    status = "https_security_ready" if not [f for f in findings if f.severity == "ERROR"] else "blocked"
    return HttpsSecurityReport(
        status=status,
        findings=tuple(findings),
        endpoints=tuple(endpoints),
        safety_boundary={
            "connects_to_network": False,
            "prints_raw_urls": False,
            "prints_secrets": False,
            "validates_tls_contract_offline": True,
        },
    )


def load_json_config(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("config_root_must_be_object")
    return data


def redacted_url_summary(url: str) -> dict[str, Any]:
    parsed = urlparse(str(url))
    host = parsed.hostname or ""
    return {
        "scheme": parsed.scheme,
        "host_hash": _hash(host) if host else "",
        "host_redacted": bool(host),
        "port_present": parsed.port is not None,
        "path_depth": len([part for part in parsed.path.split("/") if part]),
    }


def _walk(value: Any, path: str, findings: list[HttpsFinding], endpoints: list[dict[str, Any]]) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if key_text.lower() in FORBIDDEN_SECRET_KEYS and nested not in {"", None, "REPLACE_WITH_SECRET_IN_PRIVATE_VAULT"}:
                findings.append(_finding("secret_like_value_not_allowed", "ERROR", child_path))
            if isinstance(nested, str):
                _validate_field_url(key_text, nested, child_path, findings, endpoints)
            _walk(nested, child_path, findings, endpoints)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _walk(nested, f"{path}[{index}]", findings, endpoints)


def _validate_field_url(
    key: str,
    value: str,
    path: str,
    findings: list[HttpsFinding],
    endpoints: list[dict[str, Any]],
) -> None:
    text = value.strip()
    if "://" not in text:
        return
    key_lower = key.lower()
    parsed = urlparse(text)
    endpoints.append({"field_path": path, **redacted_url_summary(text)})
    if key_lower in HTTPS_FIELDS and parsed.scheme != "https":
        findings.append(_finding("https_required", "ERROR", path))
    elif key_lower in LDAPS_FIELDS and parsed.scheme != "ldaps":
        findings.append(_finding("ldaps_required", "ERROR", path))
    elif key_lower in LOCAL_HTTP_FIELDS and parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        findings.append(_finding("only_localhost_http_redirect_allowed", "ERROR", path))
    elif parsed.scheme == "http" and key_lower not in LOCAL_HTTP_FIELDS:
        findings.append(_finding("plain_http_not_allowed", "ERROR", path))


def _finding(code: str, severity: str, path: str) -> HttpsFinding:
    return HttpsFinding(
        code=code,
        severity=severity,
        field_path=path,
        message=code.replace("_", " "),
    )


def _hash(value: str) -> str:
    return hashlib.sha256(value.lower().encode("utf-8")).hexdigest()[:16]
