from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable


CAPABILITY_CORE_SEMANTICS = "core_semantics"
CAPABILITY_DESKTOP_SURFACE = "desktop_surface"
CAPABILITY_RUNTIME_GUARD = "runtime_guard"
CAPABILITY_XLSX_DASHBOARD = "xlsx_dashboard"
CAPABILITY_SHARED_CATALOG = "shared_catalog"
CAPABILITY_DIAG_SURFACE = "diag_surface"
DEFAULT_PROFILE_NAME = "full"


@dataclass(frozen=True)
class RuntimeProfile:
    name: str
    description: str
    capabilities: frozenset[str]

    def enables(self, capability: str) -> bool:
        return str(capability).strip() in self.capabilities


@dataclass(frozen=True)
class XlsxDashboardEngine:
    aggregate_long: Callable[..., Any]
    build_workbook: Callable[..., Any]
    source_module: str


class CapabilityUnavailableError(RuntimeError):
    pass


_PROFILE_REGISTRY = {
    "full": RuntimeProfile(
        name="full",
        description="Desktop completo com exportacao XLSX, catalogo compartilhado e superfícies auxiliares.",
        capabilities=frozenset(
            {
                CAPABILITY_CORE_SEMANTICS,
                CAPABILITY_DESKTOP_SURFACE,
                CAPABILITY_RUNTIME_GUARD,
                CAPABILITY_XLSX_DASHBOARD,
                CAPABILITY_SHARED_CATALOG,
                CAPABILITY_DIAG_SURFACE,
            }
        ),
    ),
    "lite": RuntimeProfile(
        name="lite",
        description="Desktop principal com o mesmo output util, mantendo capacidades essenciais e carregamento tardio das opcionais.",
        capabilities=frozenset(
            {
                CAPABILITY_CORE_SEMANTICS,
                CAPABILITY_DESKTOP_SURFACE,
                CAPABILITY_RUNTIME_GUARD,
                CAPABILITY_XLSX_DASHBOARD,
                CAPABILITY_SHARED_CATALOG,
            }
        ),
    ),
    "diag": RuntimeProfile(
        name="diag",
        description="Perfil com superficies de apoio e diagnostico habilitadas explicitamente.",
        capabilities=frozenset(
            {
                CAPABILITY_CORE_SEMANTICS,
                CAPABILITY_DESKTOP_SURFACE,
                CAPABILITY_RUNTIME_GUARD,
                CAPABILITY_XLSX_DASHBOARD,
                CAPABILITY_SHARED_CATALOG,
                CAPABILITY_DIAG_SURFACE,
            }
        ),
    ),
}


def normalize_profile_name(raw: object) -> str:
    text = str(raw or "").strip().lower()
    if text in _PROFILE_REGISTRY:
        return text
    return DEFAULT_PROFILE_NAME


def get_runtime_profile(profile_name: object | None = None) -> RuntimeProfile:
    if profile_name is None:
        profile_name = os.environ.get("ANDY_PROFILE", "")
    return _PROFILE_REGISTRY[normalize_profile_name(profile_name)]


def capability_enabled(capability: str, *, profile_name: object | None = None) -> bool:
    return get_runtime_profile(profile_name).enables(capability)


@lru_cache(maxsize=8)
def load_xlsx_dashboard_engine(profile_name: object | None = None) -> XlsxDashboardEngine:
    profile = get_runtime_profile(profile_name)
    if not profile.enables(CAPABILITY_XLSX_DASHBOARD):
        raise CapabilityUnavailableError(
            f"Perfil '{profile.name}' nao habilita a capability '{CAPABILITY_XLSX_DASHBOARD}'."
        )

    try:
        module = importlib.import_module("andys_report_runner")
    except Exception as exc:  # pragma: no cover - exercised through callers
        raise CapabilityUnavailableError("Motor XLSX indisponivel neste ambiente.") from exc

    aggregate_long = getattr(module, "aggregate_long", None)
    build_workbook = getattr(module, "construir_bi_excel_multi_equip_multi_var_long", None)
    if not callable(aggregate_long) or not callable(build_workbook):
        raise CapabilityUnavailableError("Motor XLSX carregado sem a interface esperada.")

    return XlsxDashboardEngine(
        aggregate_long=aggregate_long,
        build_workbook=build_workbook,
        source_module="andys_report_runner",
    )


def clear_optional_capability_caches() -> None:
    load_xlsx_dashboard_engine.cache_clear()
