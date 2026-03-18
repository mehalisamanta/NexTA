"""
Compatibility shim for legacy third-party packages that expect a top-level
`exceptions` module providing `PendingDeprecationWarning`.

This works around an import inside an older `docx` implementation that does:
`from exceptions import PendingDeprecationWarning`.
"""

from __future__ import annotations


class PendingDeprecationWarning(Warning):
    """
    Local definition mirroring the built-in `PendingDeprecationWarning`.

    Some outdated libraries import this from a standalone `exceptions`
    module which no longer exists in modern Python versions.
    """