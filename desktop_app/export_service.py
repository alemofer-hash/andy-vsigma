from __future__ import annotations

import datetime as dt
import getpass
import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import pandas as pd
from openpyxl import load_workbook

from audit.export_auditor import ExportIntent, estimate_export_shape, run_audit
from security.audit import audit_export, audit_export_risk
from xlsx_selection import expand_pairs, normalize_selections, pontos_to_xlsx_selection, validate_selections

from desktop_app.models import DesktopRuntimeState, ExportAuditResult, ExportOptions, QueryFilters
from desktop_app.maneuver_dashboard import append_maneuver_dashboard_sheets, detect_dashboard_maneuvers
from desktop_app.query_service import DesktopQueryService

try:
    from andys_report_runner import aggregate_long, construir_bi_excel_multi_equip_multi_var_long
    BI_IMPORT_ERROR = None
except Exception as exc:
    aggregate_long = None
    construir_bi_excel_multi_equip_multi_var_long = None
    BI_IMPORT_ERROR = exc


class ExportAmbiguityError(ValueError):
    pass


def _is_ambiguity_error(message: str) -> bool:
    text = str(message or "").lower()
    return "ambiguidade" in text or "ambiguous" in text


def run_report(**kwargs: Any) -> str:
    if BI_IMPORT_ERROR is not None or construir_bi_excel_multi_equip_multi_var_long is None:
        raise RuntimeError("Motor BI indisponivel neste ambiente.")
    raise RuntimeError("run_report_legacy_requires_test_or_adapter")


# --- NEW: desktop export service extracted from the Streamlit export flow ---
class DesktopExportService:
    def __init__(
        self,
        runtime_state: DesktopRuntimeState | None = None,
        *,
        work_root: str | None = None,
        db_path: str | None = None,
    ) -> None:
        if runtime_state is None:
            root = Path(work_root or ".").resolve()
            runtime_state = DesktopRuntimeState(
                layout={
                    "exports": root,
                    "audit_log_path": root / "audit.jsonl",
                },
                settings={"export_dir": str(root)},
                source_root="",
                source_reason="test_compat",
                source_mode="test",
                source_exists=False,
                source_is_unc=False,
                source_file_count=0,
                db_path=str(Path(db_path or (root / "andys.duckdb")).resolve()),
                db_exists=Path(db_path or (root / "andys.duckdb")).exists(),
                setup_required=False,
                settings_path=str(root / "settings.json"),
                last_index={},
            )
        self.runtime_state = runtime_state
        self.user_id = getpass.getuser()
        self.role = str(os.environ.get("ANDYS_ROLE", "admin")).strip().lower() or "admin"

    def _export_xlsx_dashboard_legacy(self, options: ExportOptions) -> str:
        try:
            return run_report(
                equips=list(options.equips),
                t0=options.t0,
                t1=options.t1,
                vars_=list(options.vars_),
                agg=options.agg,
                time_floor=options.time_floor,
                equip_slots=options.equip_slots,
                var_slots=options.var_slots,
                max_timestamps=options.max_timestamps,
                out_dir=options.out_dir,
                out_name=options.out_name,
                template_path=options.template_path,
                include_patamar=bool(options.include_patamar),
                patamar_p_vars=list(options.patamar_p_vars or []) or None,
                patamar_q_vars=list(options.patamar_q_vars or []) or None,
                patamar_principal_p_key=options.patamar_principal_p_key,
                patamar_principal_q_key=options.patamar_principal_q_key,
            )
        except ValueError as exc:
            if _is_ambiguity_error(str(exc)):
                raise ExportAmbiguityError(str(exc)) from exc
            raise

    # --- NEW: safe directory creation for desktop export destinations ---
    def _ensure_dir(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)

    # --- NEW: equipment derivation from resolved point identifiers ---
    def _equip_ids_from_pontos(self, selected_pontos: List[str]) -> List[str]:
        equips: set[str] = set()
        for ponto in selected_pontos or []:
            parts = str(ponto).split("|")
            if len(parts) < 3:
                continue
            equip = str(parts[2]).strip()
            if equip:
                equips.add(equip)
        return sorted(equips)

    # --- NEW: audit-log filter payload reused by desktop risk/export events ---
    def _sanitize_audit_filters(
        self,
        *,
        filters: QueryFilters,
        selected_pontos: List[str],
        options: ExportOptions,
    ) -> Dict[str, Any]:
        t0, t1 = DesktopQueryService.month_selection_bounds(int(filters.ano), list(filters.meses_sel))
        return {
            "t0": t0[:19],
            "t1": t1[:19],
            "n_equips": len(self._equip_ids_from_pontos(selected_pontos)),
            "n_vars": len(filters.vars_sel),
            "agg": options.agg,
            "time_floor": str(options.time_floor or "")[:16],
            "max_timestamps": int(options.max_timestamps),
        }

    # --- NEW: compact audit finding serialization for the persisted desktop audit log ---
    def _serialize_findings(self, findings: List[Any]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for finding in findings:
            out.append(
                {
                    "code": str(getattr(finding, "code", "")),
                    "severity": str(getattr(finding, "severity", "")),
                    "title": str(getattr(finding, "title", "")),
                    "hard_stop": bool(getattr(finding, "hard_stop", False)),
                }
            )
        return out

    # --- NEW: desktop export-audit result before any file is generated ---
    def audit(self, query_service: DesktopQueryService, filters: QueryFilters, options: ExportOptions) -> ExportAuditResult:
        where_sql, where_params = query_service.build_where(filters)
        con = duckdb.connect(self.runtime_state.db_path, read_only=True)
        try:
            intent = ExportIntent(
                format=options.fmt,  # type: ignore[arg-type]
                include_metadata=True,
                destination_excel=bool(options.destination_excel),
                agg=str(options.agg),
                time_floor=(str(options.time_floor or "").strip() or None),
                max_timestamps=int(options.max_timestamps),
            )
            metrics = estimate_export_shape(
                con=con,
                where_sql=where_sql,
                where_params=where_params,
                intent=intent,
            )
            findings = run_audit(metrics=metrics, intent=intent)
        finally:
            con.close()

        if any(str(getattr(f, "severity", "")) == "ERROR" and bool(getattr(f, "hard_stop", False)) for f in findings):
            status = "ERROR"
        elif any(str(getattr(f, "severity", "")) == "WARN" for f in findings):
            status = "WARN"
        else:
            status = "OK"
        return ExportAuditResult(status=status, metrics=metrics, findings=findings)

    # --- NEW: default export destination under the desktop workspace ---
    def default_output_path(self, filename: str) -> str:
        export_dir = str(self.runtime_state.settings.get("export_dir", self.runtime_state.layout["exports"]))
        self._ensure_dir(export_dir)
        return str((Path(export_dir) / filename).resolve())

    # --- NEW: desktop CSV LONG export reusing the existing lake query logic ---
    def export_csv_long(
        self,
        query_service: DesktopQueryService,
        filters: QueryFilters,
        *,
        output_path: Optional[str] = None,
        limit_cap: Optional[int] = None,
    ) -> str:
        df_long = query_service.query_full_long(filters=filters, limit_cap=limit_cap)
        if df_long.empty:
            raise ValueError("Recorte vazio: ajuste filtros antes de exportar.")
        out_path = output_path or self.default_output_path("sentinela_export_long.csv")
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        df_long.to_csv(out_path, index=False, encoding="utf-8")
        audit_export(
            user_id=self.user_id,
            role=self.role,
            rowcount=len(df_long),
            filters={
                "ano": filters.ano,
                "meses": list(filters.meses_sel),
                "se": list(filters.se_sel),
                "bay": list(filters.bay_sel),
                "equips_selected": list(filters.equipamento_sel),
                "terminal_sel": list(filters.terminal_sel),
                "vars_sel": list(filters.vars_sel),
                "ponto_id_like": filters.ponto_id_like,
            },
            file_path=out_path,
            audit_log_path=str(self.runtime_state.layout["audit_log_path"]),
        )
        return out_path

    # --- NEW: desktop CSV WIDE export reusing the current pivot semantics ---
    def export_csv_wide(
        self,
        query_service: DesktopQueryService,
        filters: QueryFilters,
        *,
        output_path: Optional[str] = None,
        limit_cap: Optional[int] = None,
    ) -> str:
        df_long = query_service.query_full_long(filters=filters, limit_cap=limit_cap)
        if df_long.empty:
            raise ValueError("Recorte vazio: ajuste filtros antes de exportar.")
        df_tmp = df_long.copy()
        df_tmp["timestamp"] = pd.to_datetime(df_tmp["timestamp"], errors="coerce")
        df_tmp = df_tmp.dropna(subset=["timestamp", "EQUIPAMENTO", "var"])
        wide = (
            df_tmp.pivot_table(
                index=["timestamp", "SE", "BAY", "EQUIPAMENTO", "TERMINAL", "ponto_id"],
                columns="var",
                values="valor",
                aggfunc="last",
            )
            .reset_index()
        )
        out_path = output_path or self.default_output_path("sentinela_export_wide.csv")
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        wide.to_csv(out_path, index=False, encoding="utf-8")
        audit_export(
            user_id=self.user_id,
            role=self.role,
            rowcount=len(wide),
            filters={
                "ano": filters.ano,
                "meses": list(filters.meses_sel),
                "se": list(filters.se_sel),
                "bay": list(filters.bay_sel),
                "equips_selected": list(filters.equipamento_sel),
                "terminal_sel": list(filters.terminal_sel),
                "vars_sel": list(filters.vars_sel),
                "ponto_id_like": filters.ponto_id_like,
            },
            file_path=out_path,
            audit_log_path=str(self.runtime_state.layout["audit_log_path"]),
        )
        return out_path

    # --- NEW: normalize export input for the existing XLSX BI engine ---
    def _normalize_for_agg(self, df_long: pd.DataFrame) -> pd.DataFrame:
        req = ["timestamp", "equip_id", "var", "classe", "valor"]
        missing = [c for c in req if c not in df_long.columns]
        if missing:
            raise ValueError(f"Colunas ausentes no LONG: {missing}")

        extra_cols = [c for c in ["SE", "BAY", "TERMINAL"] if c in df_long.columns]
        df = df_long[req + extra_cols].copy()
        if "EQUIPAMENTO" in df_long.columns:
            equip = df_long["EQUIPAMENTO"].astype(str).str.strip()
            if equip.ne("").any():
                df["equip_id"] = equip
        elif "ponto_id" in df_long.columns:
            ponto = df_long["ponto_id"].astype(str).str.strip()
            if ponto.ne("").any():
                df["equip_id"] = ponto
        ts = pd.to_datetime(df["timestamp"], errors="coerce")
        if getattr(ts.dt, "tz", None) is not None:
            ts = ts.dt.tz_convert(None)
        ts = ts.dt.floor("s")
        df["timestamp"] = ts
        df["equip_id"] = df["equip_id"].astype(str)
        df["var"] = df["var"].astype(str)
        df["classe"] = df["classe"].fillna("").astype(str)
        if "SE" not in df.columns:
            df["SE"] = ""
        if "BAY" not in df.columns:
            df["BAY"] = ""
        if "TERMINAL" not in df.columns:
            df["TERMINAL"] = ""
        df["SE"] = df["SE"].fillna("").astype(str)
        df["BAY"] = df["BAY"].fillna("").astype(str)
        df["TERMINAL"] = df["TERMINAL"].fillna("").astype(str)
        df = df.dropna(subset=["timestamp", "equip_id", "var", "valor"])
        return df

    # --- NEW: normalize aggregated schema so the BI engine receives the expected contract ---
    def _normalize_agg_schema(self, df_agg: pd.DataFrame) -> pd.DataFrame:
        expected = ["_TS", "_KEY", "_VAL", "_SE", "_BAY", "_TERMINAL", "_EQUIP", "_VAR", "_CLASSE"]

        if set(expected).issubset(df_agg.columns):
            out = df_agg.copy()
        elif {"timestamp", "equip_id", "var", "classe", "valor"}.issubset(df_agg.columns):
            out = df_agg.rename(
                columns={
                    "timestamp": "_TS",
                    "SE": "_SE",
                    "BAY": "_BAY",
                    "TERMINAL": "_TERMINAL",
                    "equip_id": "_EQUIP",
                    "var": "_VAR",
                    "classe": "_CLASSE",
                    "valor": "_VAL",
                }
            ).copy()
            out["_SE"] = out.get("_SE", "").astype(str)
            out["_BAY"] = out.get("_BAY", "").astype(str)
            out["_TERMINAL"] = out.get("_TERMINAL", "").astype(str)
            out["_KEY"] = (
                out["_SE"].fillna("").astype(str)
                + "|"
                + out["_BAY"].fillna("").astype(str)
                + "|"
                + out["_EQUIP"].astype(str)
                + "|"
                + out["_TERMINAL"].fillna("").astype(str)
                + "|"
                + out["_VAR"].astype(str)
            )
        else:
            raise ValueError(f"Schema de df_agg inesperado. Colunas: {list(df_agg.columns)}")

        out["_TS"] = pd.to_datetime(out["_TS"], errors="coerce")
        out["_SE"] = out.get("_SE", "").fillna("").astype(str)
        out["_BAY"] = out.get("_BAY", "").fillna("").astype(str)
        out["_TERMINAL"] = out.get("_TERMINAL", "").fillna("").astype(str)
        out["_EQUIP"] = out["_EQUIP"].astype(str)
        out["_VAR"] = out["_VAR"].astype(str)
        out["_CLASSE"] = out["_CLASSE"].fillna("").astype(str)
        out["_KEY"] = out["_KEY"].astype(str)
        out = out.dropna(subset=["_TS", "_VAL", "_EQUIP", "_VAR"])
        return out[expected]

    # --- NEW: compatibility wrapper for the existing XLSX report engine signatures ---
    def _call_xlsx_engine(
        self,
        *,
        df_agg: pd.DataFrame,
        out_path: str,
        options: ExportOptions,
        report_meta: Dict[str, str],
        selected_pairs: Optional[List[Tuple[str, str]]] = None,
    ) -> Tuple[str, List[str]]:
        try:
            result = construir_bi_excel_multi_equip_multi_var_long(
                long_df=df_agg,
                xlsx_out=out_path,
                report_meta=report_meta,
                equip_slots=int(options.equip_slots),
                var_slots=int(options.var_slots),
                max_timestamps=int(options.max_timestamps),
                selected_pairs=selected_pairs,
            )
        except TypeError:
            result = construir_bi_excel_multi_equip_multi_var_long(
                long_df=df_agg,
                xlsx_out=out_path,
                equip_slots=int(options.equip_slots),
                var_slots=int(options.var_slots),
                max_timestamps=int(options.max_timestamps),
            )
        if isinstance(result, tuple) and len(result) == 2:
            return str(result[0]), list(result[1] or [])
        return str(result), []

    def _timestamp_chunk_frames(self, df_agg: pd.DataFrame, max_timestamps: int) -> List[pd.DataFrame]:
        if "_TS" not in df_agg.columns or int(max_timestamps or 0) <= 0:
            return [df_agg.copy()]
        ts_values = pd.to_datetime(df_agg["_TS"], errors="coerce").dropna()
        unique_ts = pd.Series(ts_values.unique()).sort_values(kind="stable").reset_index(drop=True)
        if len(unique_ts.index) <= int(max_timestamps):
            return [df_agg.copy()]

        work = df_agg.copy()
        work["_SENTINELA_TS_CHUNK"] = pd.to_datetime(work["_TS"], errors="coerce")
        chunks: List[pd.DataFrame] = []
        for start in range(0, len(unique_ts.index), int(max_timestamps)):
            allowed = set(unique_ts.iloc[start : start + int(max_timestamps)].tolist())
            chunk = work[work["_SENTINELA_TS_CHUNK"].isin(allowed)].drop(columns=["_SENTINELA_TS_CHUNK"]).copy()
            if not chunk.empty:
                chunks.append(chunk)
        return chunks or [df_agg.copy()]

    def _dashboard_part_name(self, zip_path: Path, part_index: int, part_total: int) -> str:
        stem = zip_path.stem or "sentinela_dashboard"
        return f"{stem}_parte_{part_index:02d}_de_{part_total:02d}.xlsx"

    def _append_maneuver_tabs(
        self,
        *,
        workbook_path: str,
        df_agg: pd.DataFrame,
        filters: QueryFilters,
        selected_pontos: List[str],
        generated_at: str,
    ) -> Tuple[bool, List[str]]:
        warnings: List[str] = []
        if df_agg.empty:
            return False, warnings
        workbook = load_workbook(workbook_path)
        try:
            candidates, episodes, maneuver_warnings = detect_dashboard_maneuvers(
                df_agg,
                selected_variables=filters.vars_sel,
                selected_feeders=[*filters.bay_sel, *selected_pontos],
                settings=self.runtime_state.settings,
                source_alias="sentinela_dashboard_export",
            )
            warnings.extend(maneuver_warnings)
            append_maneuver_dashboard_sheets(
                workbook,
                candidates=candidates,
                episodes=episodes,
                warnings=maneuver_warnings,
                generated_at=generated_at,
            )
            workbook.save(workbook_path)
            return True, warnings
        finally:
            workbook.close()

    # --- NEW: desktop XLSX dashboard export reusing the current BI engine and audit trail ---
    def export_xlsx_dashboard(
        self,
        query_service: DesktopQueryService | ExportOptions,
        filters: QueryFilters | None = None,
        *,
        selected_pontos: Optional[List[str]] = None,
        output_path: Optional[str] = None,
        options: Optional[ExportOptions] = None,
    ) -> Tuple[str, List[str]]:
        if isinstance(query_service, ExportOptions):
            return self._export_xlsx_dashboard_legacy(query_service), []
        if filters is None:
            raise ValueError("Filtros sao obrigatorios para exportacao XLSX operacional.")
        selected_pontos = list(selected_pontos or [])
        export_options = options or ExportOptions(fmt="xlsx_dashboard")
        if BI_IMPORT_ERROR is not None or aggregate_long is None or construir_bi_excel_multi_equip_multi_var_long is None:
            raise RuntimeError("Motor BI indisponivel neste ambiente.")
        if not selected_pontos:
            raise ValueError("Selecione ao menos 1 ponto para gerar o XLSX.")
        if not filters.vars_sel:
            raise ValueError("Selecione ao menos 1 variavel para gerar o XLSX.")

        selections = normalize_selections(pontos_to_xlsx_selection(selected_pontos, filters.vars_sel))
        equips_for_export = self._equip_ids_from_pontos(selected_pontos)
        missing_cfg = [e for e in equips_for_export if e not in selections]
        empty_vars = [e for e in equips_for_export if not selections.get(e)]
        if missing_cfg or empty_vars:
            pending = sorted(set(missing_cfg + empty_vars))
            raise ValueError("Selecione ao menos 1 variavel para cada equipamento. Pendentes: " + ", ".join(pending[:12]))
        validate_selections(selections, required_equips=equips_for_export)
        selected_pairs = expand_pairs(selections)
        if not selected_pairs:
            raise ValueError("Selecione ao menos 1 par equipamento/variavel para o XLSX.")

        df_long = query_service.query_full_long(filters=filters, limit_cap=export_options.limit_cap)
        if df_long.empty:
            raise ValueError("Recorte vazio: ajuste filtros antes de gerar o XLSX.")
        df_input = self._normalize_for_agg(df_long)
        df_agg = aggregate_long(df_input, agg=export_options.agg, time_floor=(str(export_options.time_floor or "").strip() or None))
        df_agg = self._normalize_agg_schema(df_agg)
        keep_pairs = {(eq, vv) for eq, vv in selected_pairs}
        pair_idx = pd.MultiIndex.from_frame(df_agg[["_EQUIP", "_VAR"]].astype(str))
        df_agg = df_agg[pair_idx.isin(list(keep_pairs))].copy()
        if df_agg.empty:
            raise ValueError("Apos agregacao, o recorte ficou vazio para os pares selecionados.")

        out_path = output_path or self.default_output_path("sentinela_dashboard.xlsx")
        report_meta = {
            "equips": ", ".join(sorted(selections.keys())),
            "t0": DesktopQueryService.month_selection_bounds(int(filters.ano), list(filters.meses_sel))[0],
            "t1": DesktopQueryService.month_selection_bounds(int(filters.ano), list(filters.meses_sel))[1],
            "vars": "; ".join([f"{eq}:[{', '.join(vs)}]" for eq, vs in selections.items()]),
            "selected_ponto_ids": json.dumps(selected_pontos, ensure_ascii=False),
            "agg": export_options.agg,
            "time_floor": str(export_options.time_floor or "").strip() or "(none)",
            "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        timestamp_chunks = self._timestamp_chunk_frames(df_agg, int(export_options.max_timestamps))
        if len(timestamp_chunks) > 1:
            zip_path = Path(out_path).with_suffix(".zip")
            if zip_path.exists():
                stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                zip_path = zip_path.with_name(f"{zip_path.stem}_{stamp}{zip_path.suffix}")
            zip_path.parent.mkdir(parents=True, exist_ok=True)

            warnings_list: List[str] = [
                (
                    f"Recorte com {df_agg['_TS'].nunique()} timestamps excede max_timestamps="
                    f"{int(export_options.max_timestamps)}; gerado ZIP com {len(timestamp_chunks)} workbooks completos."
                )
            ]
            maneuvers_included = False
            with tempfile.TemporaryDirectory(prefix="sentinela_xlsx_parts_") as temp_root:
                temp_dir = Path(temp_root)
                with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                    for index, chunk_df in enumerate(timestamp_chunks, start=1):
                        part_name = self._dashboard_part_name(zip_path, index, len(timestamp_chunks))
                        part_meta = dict(report_meta)
                        part_meta["period_label"] = f"{report_meta.get('period_label', '')} | Parte {index}/{len(timestamp_chunks)}"
                        part_file, part_warnings = self._call_xlsx_engine(
                            df_agg=chunk_df,
                            out_path=str(temp_dir / part_name),
                            options=export_options,
                            report_meta=part_meta,
                            selected_pairs=selected_pairs,
                        )
                        warnings_list.extend(f"Parte {index}: {warning}" for warning in part_warnings)
                        if export_options.include_maneuver_tabs:
                            included, maneuver_warnings = self._append_maneuver_tabs(
                                workbook_path=part_file,
                                df_agg=chunk_df,
                                filters=filters,
                                selected_pontos=selected_pontos,
                                generated_at=report_meta["generated_at"],
                            )
                            maneuvers_included = maneuvers_included or included
                            warnings_list.extend(f"Parte {index}: {warning}" for warning in maneuver_warnings)
                        archive.write(part_file, arcname=part_name)

            audit_export(
                user_id=self.user_id,
                role=self.role,
                rowcount=len(df_agg),
                filters={
                    "ano": filters.ano,
                    "meses": list(filters.meses_sel),
                    "se": list(filters.se_sel),
                    "bay": list(filters.bay_sel),
                    "equips_selected": list(filters.equipamento_sel),
                    "selected_pontos": list(selected_pontos),
                    "terminal_sel": list(filters.terminal_sel),
                    "vars_sel": list(filters.vars_sel),
                    "ponto_id_like": filters.ponto_id_like,
                    "maneuvers_included": maneuvers_included,
                    "zip_parts": len(timestamp_chunks),
                },
                file_path=str(zip_path),
                audit_log_path=str(self.runtime_state.layout["audit_log_path"]),
            )
            return str(zip_path), warnings_list

        try:
            out_file, warns = self._call_xlsx_engine(
                df_agg=df_agg,
                out_path=out_path,
                options=export_options,
                report_meta=report_meta,
                selected_pairs=selected_pairs,
            )
        except PermissionError:
            alt_name = f"sentinela_dashboard_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            out_file, warns = self._call_xlsx_engine(
                df_agg=df_agg,
                out_path=self.default_output_path(alt_name),
                options=export_options,
                report_meta=report_meta,
                selected_pairs=selected_pairs,
            )

        warnings_list = list(warns)
        maneuvers_included = False
        if export_options.include_maneuver_tabs:
            try:
                maneuvers_included, maneuver_warnings = self._append_maneuver_tabs(
                    workbook_path=out_file,
                    df_agg=df_agg,
                    filters=filters,
                    selected_pontos=selected_pontos,
                    generated_at=report_meta["generated_at"],
                )
                warnings_list.extend(maneuver_warnings)
            except Exception as exc:
                warnings_list.append(f"Manobras nao anexadas ao XLSX: {exc}")

        audit_export(
            user_id=self.user_id,
            role=self.role,
            rowcount=len(df_agg),
            filters={
                "ano": filters.ano,
                "meses": list(filters.meses_sel),
                "se": list(filters.se_sel),
                "bay": list(filters.bay_sel),
                "equips_selected": list(filters.equipamento_sel),
                "selected_pontos": list(selected_pontos),
                "terminal_sel": list(filters.terminal_sel),
                "vars_sel": list(filters.vars_sel),
                "ponto_id_like": filters.ponto_id_like,
                "maneuvers_included": maneuvers_included,
            },
            file_path=out_file,
            audit_log_path=str(self.runtime_state.layout["audit_log_path"]),
        )
        return out_file, warnings_list

    # --- NEW: desktop audit log entry when user confirms export with warnings ---
    def persist_risk_decision(
        self,
        *,
        filters: QueryFilters,
        options: ExportOptions,
        audit_result: ExportAuditResult,
        selected_pontos: List[str],
        action_taken: str,
    ) -> None:
        audit_export_risk(
            user_id=self.user_id,
            role=self.role,
            intent={"format": options.fmt, "destination_excel": options.destination_excel},
            filters=self._sanitize_audit_filters(filters=filters, selected_pontos=selected_pontos, options=options),
            metrics=audit_result.metrics,
            findings=self._serialize_findings(audit_result.findings),
            action_taken=action_taken,
            audit_log_path=str(self.runtime_state.layout["audit_log_path"]),
        )
