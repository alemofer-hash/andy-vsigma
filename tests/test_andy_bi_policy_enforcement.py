from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

import duckdb
import pytest

from andy_bi.enforcement import PolicyEnforcementDenied, evaluate_boundary_policy
from andy_boundary.operations import execute_boundary_request, make_boundary_request


ROOT = Path(__file__).resolve().parents[1]
TENANT_POLICY = ROOT / "config" / "andy_bi_tenant_policy.example.json"


def _mk_root(name: str) -> Path:
    root = (Path(".validation_tmp") / f"{name}_{uuid.uuid4().hex[:8]}").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _mk_db(root: Path) -> Path:
    db_path = (root / "andys.duckdb").resolve()
    con = duckdb.connect(str(db_path))
    try:
        con.execute(
            """
            CREATE TABLE medicoes (
                timestamp TIMESTAMP,
                ano INTEGER,
                mes INTEGER,
                SE VARCHAR,
                BAY VARCHAR,
                EQUIPAMENTO VARCHAR,
                TERMINAL VARCHAR,
                ponto_id VARCHAR,
                equip_id VARCHAR,
                var VARCHAR,
                classe VARCHAR,
                valor DOUBLE
            );
            """
        )
        con.execute(
            """
            INSERT INTO medicoes VALUES
            ('2026-03-19 14:45:00', 2026, 3, 'SE1', 'B1', 'EQ1', 'T1', 'SE1|B1|EQ1|T1', 'EQ1', 'IA', 'analog', 10.5);
            """
        )
    finally:
        con.close()
    return db_path


def _enabled_mock_file(tmp_path: Path) -> Path:
    source = ROOT / "config" / "andy_bi_mock_claims.example.json"
    target = tmp_path / "andy_bi_mock_claims.private.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    data["mock_enabled"] = True
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def _bi_payload(*, mock_file: Path, identity_key: str, tenant_id: str, state: str, source_root: str) -> dict[str, object]:
    return {
        "bi_policy": {
            "enabled": True,
            "identity_key": identity_key,
            "mock_claims_file": str(mock_file),
            "tenant_policy_file": str(TENANT_POLICY),
        },
        "bi_scope": {
            "tenant_id": tenant_id,
            "state": state,
            "source_root": source_root,
        },
    }


def test_policy_enforcement_is_disabled_by_default() -> None:
    result = evaluate_boundary_policy("query.page", {"db_path": "ignored.duckdb"})

    assert result.status == "disabled"
    assert result.allowed is True
    assert result.safety["connects_to_corporate_network"] is False


def test_boundary_query_preserves_existing_behavior_when_policy_disabled() -> None:
    root = _mk_root("bi_policy_disabled_query")
    try:
        db_path = _mk_db(root)
        request = make_boundary_request(
            "query.page",
            {
                "db_path": str(db_path),
                "filters": {"ano": 2026, "meses_sel": [3]},
                "page_size": 10,
                "page_number": 1,
            },
        )

        result = execute_boundary_request(request)

        assert result["kind"] == "page_result"
        assert result["payload"]["total"] == 1
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_boundary_query_allows_in_scope_mock_engineer(tmp_path: Path) -> None:
    root = _mk_root("bi_policy_allowed_query")
    try:
        db_path = _mk_db(root)
        payload = {
            "db_path": str(db_path),
            "filters": {"ano": 2026, "meses_sel": [3]},
            **_bi_payload(
                mock_file=_enabled_mock_file(tmp_path),
                identity_key="mock_engineer_rs",
                tenant_id="DISTRIBUTOR_RS_PLACEHOLDER",
                state="RS",
                source_root="${ANDY_BI_RS_SOURCE_ROOT}",
            ),
        }

        result = execute_boundary_request(make_boundary_request("query.page", payload))

        assert result["kind"] == "page_result"
        assert result["payload"]["total"] == 1
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_boundary_query_denies_out_of_scope_before_db_execution(tmp_path: Path) -> None:
    payload = {
        "db_path": "missing_should_not_be_opened.duckdb",
        **_bi_payload(
            mock_file=_enabled_mock_file(tmp_path),
            identity_key="mock_engineer_rs",
            tenant_id="DISTRIBUTOR_PA_PLACEHOLDER",
            state="PA",
            source_root="${ANDY_BI_PA_SOURCE_ROOT}",
        ),
    }

    with pytest.raises(PolicyEnforcementDenied) as exc_info:
        execute_boundary_request(make_boundary_request("query.page", payload))

    assert exc_info.value.result.status == "denied"
    assert exc_info.value.result.reason == "tenant_outside_identity_scope"


def test_boundary_export_denies_viewer_before_writing_file(tmp_path: Path) -> None:
    root = _mk_root("bi_policy_viewer_export")
    try:
        output_path = root / "exports" / "blocked.csv"
        payload = {
            "db_path": "missing_should_not_be_opened.duckdb",
            "runtime_root": str(root),
            "output_path": str(output_path),
            **_bi_payload(
                mock_file=_enabled_mock_file(tmp_path),
                identity_key="mock_viewer_pa",
                tenant_id="DISTRIBUTOR_PA_PLACEHOLDER",
                state="PA",
                source_root="${ANDY_BI_PA_SOURCE_ROOT}",
            ),
        }

        with pytest.raises(PolicyEnforcementDenied) as exc_info:
            execute_boundary_request(make_boundary_request("export.csv_long", payload))

        assert exc_info.value.result.status == "denied"
        assert exc_info.value.result.reason == "permission_denied:can_export"
        assert not output_path.exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_enabled_policy_requires_bi_scope(tmp_path: Path) -> None:
    payload = {
        "db_path": "missing_should_not_be_opened.duckdb",
        "bi_policy": {
            "enabled": True,
            "identity_key": "mock_engineer_rs",
            "mock_claims_file": str(_enabled_mock_file(tmp_path)),
            "tenant_policy_file": str(TENANT_POLICY),
        },
    }

    with pytest.raises(PolicyEnforcementDenied) as exc_info:
        execute_boundary_request(make_boundary_request("query.page", payload))

    assert exc_info.value.result.status == "blocked"
    assert exc_info.value.result.reason.startswith("bi_scope_required:")


def test_policy_enforcement_checker_reports_ready() -> None:
    import scripts.check_andy_bi_policy_enforcement as checker

    report = checker.build_report()

    assert report["status"] == "policy_enforcement_adapter_ready"
    assert report["checks"]["default_boundary_policy_result_is_disabled"] is True
    assert report["checks"]["enabled_policy_requires_bi_scope"] is True
    assert report["safety_boundary"]["enforcement_default_enabled"] is False
