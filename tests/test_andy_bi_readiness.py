from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "check_andy_bi_readiness.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_andy_bi_readiness", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_andy_bi_templates_are_valid_json_and_do_not_store_passwords() -> None:
    identity = json.loads((ROOT / "config" / "andy_bi_identity.example.json").read_text(encoding="utf-8"))
    tenant = json.loads((ROOT / "config" / "andy_bi_tenant_policy.example.json").read_text(encoding="utf-8"))
    environment = json.loads((ROOT / "config" / "andy_bi_environment.example.json").read_text(encoding="utf-8"))

    assert identity["security_rules"]["store_user_password"] is False
    assert identity["security_rules"]["store_client_secret"] is False
    assert identity["security_rules"]["interactive_password_login_allowed"] is False
    assert tenant["default_decision"] == "deny"
    assert environment["mode"] == "preimplementation"


def test_andy_bi_readiness_report_is_ready_for_private_inputs() -> None:
    module = _load_module()
    report = module.build_report()

    assert report["status"] == "ready_for_private_corporate_inputs"
    assert report["checks"]["required_configs_exist"] is True
    assert report["checks"]["required_docs_exist"] is True
    assert report["checks"]["private_bi_configs_not_tracked"] is True
    assert report["safety_boundary"]["connects_to_corporate_network"] is False
    assert report["safety_boundary"]["changes_analytical_engine"] is False


def test_andy_bi_docs_state_password_boundary() -> None:
    security_model = (ROOT / "docs" / "ANDY_BI_SECURITY_MODEL.md").read_text(encoding="utf-8").lower()
    identity_options = (ROOT / "docs" / "ANDY_BI_IDENTITY_OPTIONS.md").read_text(encoding="utf-8").lower()

    assert "senha nunca entra no andy" in security_model
    assert "andy nao deve guardar senha de funcionario" in identity_options
