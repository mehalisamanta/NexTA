"""
Minimal NDJSON debug logger for Cursor DEBUG MODE sessions.

Writes to `debug-d2a55d.log` in the workspace root.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional


_REPO_ROOT = Path(__file__).resolve().parents[1]
_LOG_PATH = _REPO_ROOT / "debug-d2a55d.log"
_SESSION_ID = "d2a55d"


def debug_log(
    *,
    location: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    hypothesis_id: str = "H?",
    run_id: str = "pre-fix",
) -> None:
    # #region agent log
    try:
        payload = {
            "sessionId": _SESSION_ID,
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000),
        }
        with _LOG_PATH.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(payload, separators=(",", ":")) + "\n")
    except Exception:
        # Logging must never break app execution.
        pass
    # #endregion

