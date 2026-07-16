from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from andy_threads.event_candidates import (
    apply_feedback_to_candidate,
    candidate_to_dict,
    create_centroid_candidate,
    create_power_inversion_candidate,
)
from andy_threads.feedback import (
    FeedbackEventType,
    FeedbackReasonCode,
    HumanFeedbackCaptcha,
    HumanVerdict,
    feedback_to_dict,
)
from andy_threads.models import ThreadParticipant
from andy_threads.notification_intent import NotificationChannel, build_notification_intent
from andy_threads.occurrence_store import OccurrenceStore
from andy_threads.occurrences import (
    FeedbackStatus,
    OccurrenceDomain,
    OccurrenceSeverity,
    OccurrenceStatus,
    create_occurrence,
)
from andy_threads.references import AndyThreadReference, ThreadEntityType, reference_public_summary
from andy_threads.sector_lens import SectorId


DEFAULT_OUT_DIR = ROOT / ".validation_tmp" / "andy_threads_demo_scenarios"


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    title: str
    objective: str
    owner_sector: SectorId
    target_sector: SectorId
    problem_domain: OccurrenceDomain
    severity: OccurrenceSeverity
    event_type: FeedbackEventType
    human_verdict: HumanVerdict
    reason_code: FeedbackReasonCode
    reviewer_sector: SectorId
    candidate_kind: str
    expected_review_status: str
    risk: str
    reference: AndyThreadReference


def default_scenarios() -> list[ScenarioSpec]:
    return [
        ScenarioSpec(
            scenario_id="scenario_01_power_inversion_pq",
            title="Inversao sintetica de fluxo P/Q para revisao",
            objective="Validar se Engenharia e Operacao entendem candidato de inversao sem confirmacao operacional automatica.",
            owner_sector=SectorId.ENGINEERING,
            target_sector=SectorId.OPERATION,
            problem_domain=OccurrenceDomain.POWER_INVERSION,
            severity=OccurrenceSeverity.S3_OPERATIONAL_RISK,
            event_type=FeedbackEventType.POWER_INVERSION,
            human_verdict=HumanVerdict.CORRECT,
            reason_code=FeedbackReasonCode.OPERATIONAL_SWITCHING,
            reviewer_sector=SectorId.OPERATION,
            candidate_kind="power_inversion",
            expected_review_status="HUMAN_CONFIRMED",
            risk="Falso positivo operacional se inversao for tratada como manobra confirmada.",
            reference=_reference("POWER_FLOW_EVENT", "SE_SYN_A", "AL_SYN_A", "EQ_SYN_A", "T1", "P_Q_FLOW", "synthetic-inversion"),
        ),
        ScenarioSpec(
            scenario_id="scenario_02_scada_switching",
            title="Manobra sintetica com evidencia SCADA",
            objective="Validar que somente evidencia SCADA promove candidato para confirmacao operacional.",
            owner_sector=SectorId.OPERATION,
            target_sector=SectorId.PROTECTION_AUTOMATION,
            problem_domain=OccurrenceDomain.SWITCHING_EVENT,
            severity=OccurrenceSeverity.S3_OPERATIONAL_RISK,
            event_type=FeedbackEventType.SWITCHING_EVENT,
            human_verdict=HumanVerdict.CORRECT,
            reason_code=FeedbackReasonCode.SCADA_CONFIRMS,
            reviewer_sector=SectorId.PROTECTION_AUTOMATION,
            candidate_kind="centroid",
            expected_review_status="SCADA_CONFIRMED",
            risk="Confirmar manobra sem SCADA, religador, disjuntor ou log operacional.",
            reference=_reference("POWER_FLOW_EVENT", "SE_SYN_B", "AL_SYN_B", "EQ_SYN_B", "T2", "P_Q_FLOW", "synthetic-scada"),
        ),
        ScenarioSpec(
            scenario_id="scenario_03_measurement_gap_cadence",
            title="Lacuna sintetica de medicao/cadencia",
            objective="Validar encaminhamento para Medicao/Dados quando o problema e disponibilidade do dado.",
            owner_sector=SectorId.MEASUREMENT_DATA,
            target_sector=SectorId.MEASUREMENT_DATA,
            problem_domain=OccurrenceDomain.MEASUREMENT_AVAILABILITY,
            severity=OccurrenceSeverity.S2_ENGINEERING_BLOCKER,
            event_type=FeedbackEventType.MEASUREMENT_GAP,
            human_verdict=HumanVerdict.INCOMPLETE,
            reason_code=FeedbackReasonCode.MISSING_MEASUREMENT,
            reviewer_sector=SectorId.MEASUREMENT_DATA,
            candidate_kind="diagnostic",
            expected_review_status="PARTIAL_INCOMPLETE",
            risk="Diagnostico eletrico baseado em periodo com lacuna ou cadencia inconsistente.",
            reference=_reference("MEASUREMENT_POINT", "SE_SYN_C", "AL_SYN_C", "EQ_SYN_C", "T3", "IA_IB_IC", "synthetic-gap"),
        ),
        ScenarioSpec(
            scenario_id="scenario_04_cadastre_terminal_mismatch",
            title="Divergencia sintetica de cadastro/terminal",
            objective="Validar se erro de terminal/equipamento e roteado para Cadastro sem virar evento de rede.",
            owner_sector=SectorId.CADASTRE_ASSETS,
            target_sector=SectorId.CADASTRE_ASSETS,
            problem_domain=OccurrenceDomain.CADASTRE_MAPPING,
            severity=OccurrenceSeverity.S2_ENGINEERING_BLOCKER,
            event_type=FeedbackEventType.POWER_INVERSION,
            human_verdict=HumanVerdict.NEEDS_OTHER_SECTOR,
            reason_code=FeedbackReasonCode.CADASTRE_MISMATCH,
            reviewer_sector=SectorId.ENGINEERING,
            candidate_kind="power_inversion",
            expected_review_status="HUMAN_REVIEWED",
            risk="Corrigir comportamento eletrico quando o problema real e mapeamento de ativo.",
            reference=_reference("TERMINAL", "SE_SYN_D", "AL_SYN_D", "EQ_SYN_D", "T4", "P_Q_FLOW", "synthetic-cadastre"),
        ),
        ScenarioSpec(
            scenario_id="scenario_05_export_bi_dataset",
            title="Falha sintetica de export/dashboard ou dataset BI",
            objective="Validar ocorrencia de produtividade quando a ferramenta/export nao representa o recorte esperado.",
            owner_sector=SectorId.IT_BI_DATA,
            target_sector=SectorId.IT_BI_DATA,
            problem_domain=OccurrenceDomain.EXPORT_DASHBOARD,
            severity=OccurrenceSeverity.S1_PRODUCTIVITY_BLOCKER,
            event_type=FeedbackEventType.EXPORT_DASHBOARD,
            human_verdict=HumanVerdict.INCOMPLETE,
            reason_code=FeedbackReasonCode.EXPORT_OR_QUERY_ERROR,
            reviewer_sector=SectorId.ENGINEERING,
            candidate_kind="diagnostic",
            expected_review_status="PARTIAL_INCOMPLETE",
            risk="Confundir falha de export/query com comportamento eletrico de campo.",
            reference=_reference("EXPORT_FILE", "SE_SYN_E", "AL_SYN_E", "EQ_SYN_E", "T5", "DASHBOARD", "synthetic-export"),
        ),
    ]


def build_scenarios_package(out_dir: Path = DEFAULT_OUT_DIR) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    scenarios_dir = out_dir / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)
    store_path = out_dir / "threads_demo_scenarios.sqlite"
    if store_path.exists():
        store_path.unlink()

    store = OccurrenceStore(store_path)
    actor = ThreadParticipant(
        subject="engineer.synthetic",
        display_name="Engenharia Sintetica",
        sector_id=SectorId.ENGINEERING.value,
        roles=("andy_threads_demo_scenarios",),
    )
    scenarios = [_build_one_scenario(store, actor, spec, scenarios_dir) for spec in default_scenarios()]
    package = {
        "status": "GO",
        "package_name": "ANDY Threads Demo Scenarios 001",
        "data_class": "synthetic",
        "real_provider_enabled": False,
        "store_path": str(store_path),
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
        "ready_for_human_review": all(item["ready_for_human_review"] for item in scenarios),
        "next_gate": "human_review_before_ui_or_corporate_store",
    }
    index_json = out_dir / "ANDY_THREADS_DEMO_SCENARIOS_001_INDEX.json"
    index_md = out_dir / "ANDY_THREADS_DEMO_SCENARIOS_001_INDEX.md"
    index_json.write_text(json.dumps(package, ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")
    index_md.write_text(render_index_markdown(package), encoding="utf-8")
    package["index_json_path"] = str(index_json)
    package["index_markdown_path"] = str(index_md)
    return package


def _build_one_scenario(
    store: OccurrenceStore,
    actor: ThreadParticipant,
    spec: ScenarioSpec,
    scenarios_dir: Path,
) -> dict[str, Any]:
    occurrence_id = f"occ-{spec.scenario_id}"
    thread_id = f"thread-{spec.scenario_id}"
    occurrence = create_occurrence(
        occurrence_id=occurrence_id,
        thread_id=thread_id,
        title=spec.title,
        summary=f"{spec.objective} Dados sinteticos; provider real desligado; nenhum evento operacional automatico.",
        problem_domain=spec.problem_domain,
        reference=spec.reference,
        owner_sector=spec.owner_sector,
        target_sector=spec.target_sector,
        created_by=actor,
        severity=spec.severity,
        tags=("synthetic", "sector_scenario", spec.scenario_id),
        metadata={"real_provider_enabled": False, "data_class": "synthetic", "scenario_id": spec.scenario_id},
    )
    store.create_occurrence(occurrence)
    forwarded = store.change_status(occurrence, OccurrenceStatus.FORWARDED, actor=actor, target_sector=spec.target_sector)
    intent = build_notification_intent(
        intent_id=f"intent-{spec.scenario_id}",
        occurrence=forwarded,
        target_channel=NotificationChannel.MANUAL_EMAIL,
        created_by=actor.subject,
    ).mark_ready_for_human_send()
    store.create_notification_intent(intent, actor=actor.subject)

    candidate_payload: dict[str, Any] | None = None
    diagnostic_payload: dict[str, Any] | None = None
    if spec.candidate_kind == "power_inversion":
        candidate = create_power_inversion_candidate(
            candidate_id=f"cand-{spec.scenario_id}",
            occurrence_id=forwarded.occurrence_id,
            thread_id=forwarded.thread_id,
            reference_key=forwarded.reference_key,
            score=0.72,
            feature_summary={"mw": -1.2, "mva": 1.5, "fp_assinado": -0.8, "synthetic": True},
            engine_version="andy-synthetic-scenarios",
            notes_redacted="Candidato sintetico de inversao; nao confirma evento operacional.",
        )
    elif spec.candidate_kind == "centroid":
        candidate = create_centroid_candidate(
            candidate_id=f"cand-{spec.scenario_id}",
            occurrence_id=forwarded.occurrence_id,
            thread_id=forwarded.thread_id,
            reference_key=forwarded.reference_key,
            score=0.81,
            centroid_metrics={"delta_norm": 0.51, "threshold": 0.30, "synthetic": True},
            engine_version="andy-synthetic-scenarios",
            notes_redacted="Centroide sintetico sinaliza candidato; SCADA e necessario para confirmar.",
        )
    else:
        candidate = None
        diagnostic_payload = {
            "diagnostic_id": f"diag-{spec.scenario_id}",
            "diagnostic_type": spec.problem_domain.value,
            "status": spec.expected_review_status,
            "source": "synthetic_demo",
            "operationally_confirmed": False,
            "notes_redacted": "Diagnostico sintetico para revisao humana; nao contem dado real.",
        }

    feedback = HumanFeedbackCaptcha(
        feedback_id=f"fb-{spec.scenario_id}",
        analysis_id=f"analysis-{spec.scenario_id}",
        occurrence_id=forwarded.occurrence_id,
        thread_id=forwarded.thread_id,
        reference_key=forwarded.reference_key,
        event_type=spec.event_type,
        human_verdict=spec.human_verdict,
        confidence_human=0.84,
        reason_code=spec.reason_code,
        target_sector=spec.target_sector,
        evidence_ref=f"synthetic-evidence-{spec.scenario_id}",
        reviewer_subject=f"{spec.reviewer_sector.value.lower()}.synthetic",
        reviewer_sector=spec.reviewer_sector,
        model_version="andy-demo-scenarios-001",
        engine_version="andy-synthetic-scenarios",
        notes_redacted="Feedback sintetico para revisar linguagem, roteamento e estados.",
        metadata={"data_class": "synthetic", "scenario_id": spec.scenario_id},
    )
    if candidate is not None:
        reviewed_candidate = apply_feedback_to_candidate(candidate, feedback)
        candidate_payload = candidate_to_dict(reviewed_candidate)
        evidence_refs = (reviewed_candidate.candidate_id, feedback.feedback_id)
        operationally_confirmed = reviewed_candidate.is_operationally_confirmed
        review_status = reviewed_candidate.status.value
    else:
        evidence_refs = (str(diagnostic_payload["diagnostic_id"]), feedback.feedback_id)
        operationally_confirmed = False
        review_status = spec.expected_review_status

    reviewed_occurrence = replace(
        forwarded,
        status=OccurrenceStatus.IN_PROGRESS,
        feedback_status=FeedbackStatus.RECEIVED,
        evidence_refs=evidence_refs,
        metadata={**forwarded.metadata, "scenario_feedback_registered": True},
    )
    store.update_occurrence(reviewed_occurrence, actor=actor, event_type="SCENARIO_FEEDBACK_REGISTERED")
    occurrence_export = store.export_occurrence(reviewed_occurrence.occurrence_id, format="json")

    payload = {
        "scenario_id": spec.scenario_id,
        "title": spec.title,
        "objective": spec.objective,
        "risk": spec.risk,
        "status": "GO",
        "data_class": "synthetic",
        "real_provider_enabled": False,
        "ready_for_human_review": True,
        "owner_sector": spec.owner_sector.value,
        "target_sector": spec.target_sector.value,
        "expected_review_status": spec.expected_review_status,
        "actual_review_status": review_status,
        "operationally_confirmed": operationally_confirmed,
        "reference": reference_public_summary(spec.reference),
        "occurrence": occurrence_export["occurrence"],
        "notification_intents": occurrence_export["notification_intents"],
        "candidate": candidate_payload,
        "diagnostic": diagnostic_payload,
        "feedback": feedback_to_dict(feedback),
        "audit_summary": occurrence_export["audit_summary"],
        "human_review_questions": _human_review_questions(spec),
    }
    json_path = scenarios_dir / f"{spec.scenario_id}.json"
    md_path = scenarios_dir / f"{spec.scenario_id}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_scenario_markdown(payload), encoding="utf-8")
    payload["json_path"] = str(json_path)
    payload["markdown_path"] = str(md_path)
    return payload


def render_scenario_markdown(payload: dict[str, Any]) -> str:
    candidate = payload.get("candidate") or {}
    diagnostic = payload.get("diagnostic") or {}
    feedback = payload["feedback"]
    occurrence = payload["occurrence"]
    intent = payload["notification_intents"][0]
    lines = [
        f"# {payload['title']}",
        "",
        f"- Scenario ID: `{payload['scenario_id']}`",
        "- Dados: `synthetic`",
        "- Provider real: `disabled`",
        f"- Status: `{payload['status']}`",
        f"- Setor dono: `{payload['owner_sector']}`",
        f"- Setor destino: `{payload['target_sector']}`",
        f"- Occurrence ID: `{occurrence['occurrence_id']}`",
        f"- Occurrence status: `{occurrence['status']}`",
        f"- Notification intent: `{intent['status']}`",
        f"- Feedback label: `{feedback['training_label']}`",
        f"- Operationally confirmed: `{payload['operationally_confirmed']}`",
        "",
        "## Objetivo",
        "",
        payload["objective"],
        "",
        "## Risco que a revisao humana deve observar",
        "",
        payload["risk"],
        "",
        "## Estado tecnico",
        "",
    ]
    if candidate:
        lines.extend(
            [
                f"- Candidate type: `{candidate['candidate_type']}`",
                f"- Candidate status: `{candidate['status']}`",
                f"- Candidate validation: `{candidate['validation_level']}`",
                f"- Candidate score: `{candidate['score']}`",
            ]
        )
    else:
        lines.extend(
            [
                f"- Diagnostic type: `{diagnostic['diagnostic_type']}`",
                f"- Diagnostic status: `{diagnostic['status']}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Perguntas para revisao humana",
            "",
        ]
    )
    for question in payload["human_review_questions"]:
        lines.append(f"- {question}")
    lines.extend(
        [
            "",
            "## Decisao da revisao",
            "",
            "| Campo | Resposta |",
            "|---|---|",
            "| Resultado | GO / PARTIAL / NO-GO |",
            "| Texto da ocorrencia esta claro? |  |",
            "| Setor destino esta correto? |  |",
            "| Falta campo tecnico? |  |",
            "| Pode ir para proximo cenario? |  |",
            "",
            "## Observacao",
            "",
            "Este pacote e sintetico. Nao houve envio real, chamada corporativa, treinamento de rede, decisao automatica ou uso de dado real.",
            "",
        ]
    )
    return "\n".join(lines)


def render_index_markdown(package: dict[str, Any]) -> str:
    lines = [
        "# ANDY Threads Demo Scenarios 001",
        "",
        f"- Status: `{package['status']}`",
        f"- Cenarios: `{package['scenario_count']}`",
        "- Dados: `synthetic`",
        "- Provider real: `disabled`",
        f"- Ready for human review: `{package['ready_for_human_review']}`",
        "",
        "## Pacotes",
        "",
        "| Cenario | Dono | Destino | Status esperado | Markdown |",
        "|---|---|---|---|---|",
    ]
    for scenario in package["scenarios"]:
        lines.append(
            "| "
            f"{scenario['scenario_id']} | "
            f"{scenario['owner_sector']} | "
            f"{scenario['target_sector']} | "
            f"{scenario['expected_review_status']} | "
            f"{scenario['markdown_path']} |"
        )
    lines.extend(
        [
            "",
            "## Gate",
            "",
            "Revisar estes cinco pacotes com Engenharia/Operacao e setores donos antes de UI ou store corporativo.",
            "",
        ]
    )
    return "\n".join(lines)


def _human_review_questions(spec: ScenarioSpec) -> list[str]:
    return [
        "O titulo comunica o problema sem ambiguidade?",
        "O setor destino e o dono correto para este tipo de ocorrencia?",
        "O texto separa candidato/diagnostico de evento confirmado?",
        "Falta algum campo tecnico obrigatorio para o setor revisar?",
        f"O risco principal foi entendido: {spec.risk}",
    ]


def _reference(
    entity_type: str,
    se: str,
    bay_or_feeder: str,
    equipamento: str,
    terminal: str,
    variavel: str,
    anomaly: str,
) -> AndyThreadReference:
    return AndyThreadReference(
        entity_type=ThreadEntityType(entity_type),
        lote_id="SYN_LOTE_THREADS_SCENARIOS_001",
        dataset_version="synthetic-scenarios-v1",
        source_fingerprint="synthetic-source-fingerprint",
        se=se,
        bay_or_feeder=bay_or_feeder,
        equipamento=equipamento,
        terminal=terminal,
        variavel=variavel,
        period_start="2026-07-10T08:00:00Z",
        period_end="2026-07-10T09:00:00Z",
        source_cadence="15min",
        filter_hash=f"synthetic-filter-{anomaly}",
        anomaly_id=anomaly,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate five synthetic ANDY Threads sector scenario packages.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Local output directory for synthetic scenario packages.")
    args = parser.parse_args(argv)

    package = build_scenarios_package(Path(args.out_dir))
    print("ANDY Threads demo scenarios: passed")
    print(f"status={package['status']}")
    print("data_class=synthetic")
    print("real_provider_enabled=false")
    print(f"scenario_count={package['scenario_count']}")
    print(f"ready_for_human_review={package['ready_for_human_review']}")
    print(f"index_markdown={package['index_markdown_path']}")
    print(f"index_json={package['index_json_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
