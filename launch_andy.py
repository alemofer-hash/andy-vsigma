from __future__ import annotations

import sys

from desktop_app.main_window import main


if __name__ == "__main__":
    raise SystemExit(main() if callable(main) else sys.exit(1))
