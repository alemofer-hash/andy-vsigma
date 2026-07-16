from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from desktop_app.models import QueryFilters
from desktop_app.thread_service import DesktopThreadService


def main() -> int:
    root = ROOT / ".validation_tmp" / "andy_threads_desktop_entrypoint"
    service = DesktopThreadService(root=root)
    result = service.create_thread_from_filters(
        QueryFilters(
            anos_sel=[2026],
            meses_sel=[5],
            se_sel=["SE_SYN"],
            bay_sel=["AL_SYN"],
            equipamento_sel=["EQ_SYN"],
            terminal_sel=["T_SYN"],
            vars_sel=["MW"],
        ),
        title="Synthetic desktop recorte thread",
        body="Synthetic check for the PySide6 desktop entrypoint service.",
    )
    stored = service.store.get_thread(result.thread_id)
    if stored["reference"].get("se") != "SE_SYN":
        print("ANDY Threads desktop entrypoint: failed")
        print("reason=reference_not_persisted")
        return 1
    print("ANDY Threads desktop entrypoint: passed")
    print(f"thread_id={result.thread_id}")
    print(f"reference={result.reference_key}")
    print(f"store={result.store_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
