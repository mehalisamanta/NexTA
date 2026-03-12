"""
Compatibility shim for legacy third-party packages that expect a top-level
`exceptions` module providing `PendingDeprecationWarning`.

This works around an import inside an older `docx` implementation that does:
`from exceptions import PendingDeprecationWarning`.
"""

from __future__ import annotations

import json
import time


class PendingDeprecationWarning(Warning):
    """
    Local definition mirroring the built-in `PendingDeprecationWarning`.

    Some outdated libraries import this from a standalone `exceptions`
    module which no longer exists in modern Python versions.
    """


def _agent_debug_log() -> None:
    """
    Minimal NDJSON log append for the debug session.

    Writes exactly one line when this module is imported so we can confirm
    that the compatibility shim was used at runtime.
    """

    # #region agent log
    try:
        payload = {
            "sessionId": "ab086e",
            "runId": "pre-fix",
            "hypothesisId": "H1",
            "location": "exceptions.py:40",
            "message": "exceptions shim imported to satisfy legacy docx dependency",
            "data": {},
            "timestamp": int(time.time() * 1000),
        }
        log_line = json.dumps(payload, separators=(",", ":")) + "\n"
        with open(
            "/Users/rishiraj/Desktop/New folder/.cursor/debug-ab086e.log",
            "a",
            encoding="utf-8",
        ) as fp:
            fp.write(log_line)
    except Exception:
        # Logging must never break application startup.
        pass
    # #endregion


_agent_debug_log()

