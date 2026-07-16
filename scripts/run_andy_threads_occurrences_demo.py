from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from andy_threads.event_candidates import apply_feedback_to_candidate, candidate_to_dict, create_centroid_candidate
from andy_threads.feedback import (
    FeedbackEventType,
    FeedbackReasonCode,
    HumanFeedbackCaptcha,
    HumanVerdict,
    feedback_to_dict,
)
from andy_threads.models import ThreadParticipant
from andy_threads.notification_intent import (
    NotificationChannel,
    build_notification_intent,
    notification_intent_to_dict,
)
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


DEFAULT_OUT_DIR = ROOT / ".validation_tmp" / "andy_threads_occurrences_demo"


def build_demo_payload(out_dir: Path = DEFAULT_OUT_DIR) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    store_path = out_dir / "threads_occurrences_demo.sqlite"
    if store_path.exists():
        store_path.unlink()

    actor = ThreadParticipant(
        subject="engineer.synthetic",
        display_name="Engenharia Sintetica",
        sector_id=SectorId.ENGINEERING.value,
        roles=("andy_threads_demo",),
    )
    reference = AndyThreadReference(
        entity_type=ThreadEntityType.POWER_FLOW_EVENT,
        lote_id="SYN_LOTE_2026_07_10",
        dataset_version="synthetic-demo-v1",
        source_fingerprint="synthetic-source-fingerprint",
        se="SE_SYN",
        bay_or_feeder="AL_SYN",
        equipamento="EQ_SYN",
        terminal="T1",
        variavel="P_Q_FLOW",
        period_start="2026-07-10T08:00:00Z",
        period_end="2026-07-10T09:00:00Z",
        source_cadence="15min",
        filter_hash="synthetic-filter-hash",
        anomaly_id="synthetic-switching-candidate",
    )
    store = OccurrenceStore(store_path)
    occurrence = create_occurrence(
        occurrence_id="occ-demo-threads-001",
        thread_id="thread-demo-threads-001",
        title="Candidato sintetico de manobra/inversao para revisao",
        summary=(
            "Recorte sintetico indica deslocamento estatistico compativel com candidato "
            "de manobra ou inversao. Esta demo nao usa dado real e nao confirma evento operacional."
        ),
        problem_domain=OccurrenceDomain.SWITCHING_EVENT,
        reference=reference,
        owner_sector=SectorId.ENGINEERING,
        target_sector=SectorId.OPERATION,
        created_by=actor,
        severity=OccurrenceSeverity.S2_ENGINEERING_BLOCKER,
        tags=("synthetic", "proposal_only", "threads_demo"),
        metadata={"real_provider_enabled": False, "data_class": "synthetic"},
    )
    store.create_occurrence(occurrence)

    forwarded = store.change_status(
        occurrence,
        OccurrenceStatus.FORWARDED,
        actor=actor,
        target_sector=SectorId.OPERATION,
    )
    intent = build_notification_intent(
        intent_id="intent-demo-threads-001",
        occurrence=forwarded,
        target_channel=NotificationChannel.MANUAL_EMAIL,
        created_by=actor.subject,
    ).mark_ready_for_human_send()
    store.create_notification_intent(intent, actor=actor.subject)

    candidate = create_centroid_candidate(
        candidate_id="cand-demo-centroid-001",
        occurrence_id=forwarded.occurrence_id,
        thread_id=forwarded.thread_id,
        reference_key=forwarded.reference_key,
        score=0.78,
        centroid_metrics={"delta_norm": 0.46, "threshold": 0.30, "window": "synthetic_15min"},
        model_version="centroid-theorem-proposal-v0",
        engine_version="andy-synthetic-demo",
        notes_redacted="Sinal sintetico. Centroide sinaliza candidato, nao evento confirmado.",
    )
    feedback = HumanFeedbackCaptcha(
        feedback_id="fb-demo-human-001",
        analysis_id="analysis-demo-001",
        occurrence_id=forwarded.occurrence_id,
        thread_id=forwarded.thread_id,
        reference_key=forwarded.reference_key,
        event_type=FeedbackEventType.SWITCHING_EVENT,
        human_verdict=HumanVerdict.CORRECT,
        confidence_human=0.86,
        reason_code=FeedbackReasonCode.OPERATIONAL_SWITCHING,
        target_sector=SectorId.OPERATION,
        evidence_ref="synthetic-evidence-hash-001",
        reviewer_subject="operator.synthetic",
        reviewer_sector=SectorId.OPERATION,
        model_version="centroid-theorem-proposal-v0",
        engine_version="andy-synthetic-demo",
        notes_redacted="Validacao humana sintetica: plausivel, mas sem SCADA nesta demo.",
        metadata={"data_class": "synthetic", "no_real_provider": True},
    )
    reviewed_candidate = apply_feedback_to_candidate(candidate, feedback)
    reviewed_occurrence = replace(
        forwarded,
        status=OccurrenceStatus.IN_PROGRESS,
        feedback_status=FeedbackStatus.RECEIVED,
        evidence_refs=(candidate.candidate_id, feedback.feedback_id),
        metadata={**forwarded.metadata, "demo_feedback_registered": True},
    )
    store.update_occurrence(reviewed_occurrence, actor=actor, event_type="OCCURRENCE_FEEDBACK_REGISTERED")

    occurrence_export = store.export_occurrence(reviewed_occurrence.occurrence_id, format="json")
    payload = {
        "status": "GO",
        "demo_scope": "synthetic_threads_occurrences_feedback",
        "real_provider_enabled": False,
        "data_class": "synthetic",
        "store_path": str(store_path),
        "reference": reference_public_summary(reference),
        "occurrence": occurrence_export["occurrence"],
        "notification_intents": occurrence_export["notification_intents"],
        "candidate": candidate_to_dict(reviewed_candidate),
        "feedback": feedback_to_dict(feedback),
        "audit_summary": occurrence_export["audit_summary"],
        "ready_criteria": {
            "creates_occurrence": True,
            "generates_notification_intent": True,
            "registers_feedback_captcha": True,
            "exports_redacted_summary": True,
            "provider_real_disabled": True,
            "operational_decision_applied": reviewed_candidate.is_operationally_confirmed,
        },
    }
    json_path = out_dir / "andy_threads_occurrences_demo.json"
    md_path = out_dir / "andy_threads_occurrences_demo.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_demo_markdown(payload), encoding="utf-8")
    payload["json_path"] = str(json_path)
    payload["markdown_path"] = str(md_path)
    return payload


def render_demo_markdown(payload: dict[str, Any]) -> str:
    occurrence = payload["occurrence"]
    candidate = payload["candidate"]
    feedback = payload["feedback"]
    intent = payload["notification_intents"][0]
    audit_count = len(payload["audit_summary"])
    return "\n".join(
        [
            "# ANDY Threads Occurrences Demo",
            "",
            f"- Status: `{payload['status']}`",
            "- Dados: `synthetic`",
            "- Provider real: `disabled`",
            f"- Occurrence ID: `{occurrence['occurrence_id']}`",
            f"- Occurrence status: `{occurrence['status']}`",
            f"- Notification intent: `{intent['status']}`",
            f"- Candidate status: `{candidate['status']}`",
            f"- Candidate validation: `{candidate['validation_level']}`",
            f"- Feedback label: `{feedback['training_label']}`",
            f"- Audit events: `{audit_count}`",
            "",
            "## Leitura operacional",
            "",
            "A demo prova o fluxo local: ocorrencia -> encaminhamento humano -> candidato -> feedback CAPTCHA -> resumo redigido.",
            "",
            "Nao houve envio real, chamada corporativa, treinamento de rede, decisao automatica ou uso de dado real.",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the synthetic ANDY Threads/Ocorrencias demo.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Local output directory for synthetic demo artifacts.")
    args = parser.parse_args(argv)

    payload = build_demo_payload(Path(args.out_dir))
    print("ANDY Threads occurrences demo: passed")
    print(f"status={payload['status']}")
    print("data_class=synthetic")
    print("real_provider_enabled=false")
    print(f"occurrence_id={payload['occurrence']['occurrence_id']}")
    print(f"notification_intent_status={payload['notification_intents'][0]['status']}")
    print(f"candidate_status={payload['candidate']['status']}")
    print(f"feedback_label={payload['feedback']['training_label']}")
    print(f"markdown={payload['markdown_path']}")
    print(f"json={payload['json_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
