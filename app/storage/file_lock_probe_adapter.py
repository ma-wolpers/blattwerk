"""OS adapter for `app.core.export_path_guardrails.ExportTargetLockProbe`.

Answers "can this existing file be replaced right now?" - the question `os.replace`
fails on when a viewer still holds the PDF open.

Verified on Windows 11 (spike 2026-10-27, local and in the synced 7thCloud folder): a
target held open by *any* handle - share mode R, RW, even RWD, `open(path, "rb")` or a
PyMuPDF document - makes `os.replace` fail (WinError 5). Opening the file with
``DELETE`` access and share mode ``0`` fails (ERROR_SHARING_VIOLATION, 32) in exactly
those cases. The weaker probe "DELETE with full sharing" missed the RWD case and is
therefore *not* used.

On other systems `rename` replaces open files, so nothing is ever locked.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_DELETE_ACCESS = 0x00010000
_NO_SHARING = 0
_OPEN_EXISTING = 3
_ERROR_FILE_NOT_FOUND = 2
_ERROR_PATH_NOT_FOUND = 3


class WindowsExclusiveOpenProbe:
    """`ExportTargetLockProbe` that tries an exclusive open and closes it right away."""

    def __init__(self):
        """Bind ``CreateFileW``/``CloseHandle`` once via ctypes (Windows only)."""
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateFileW.restype = wintypes.HANDLE
        kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
        ]
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self._ctypes = ctypes
        self._kernel32 = kernel32
        self._invalid = wintypes.HANDLE(-1).value

    def is_locked(self, path: Path) -> bool:
        """True if ``path`` exists and another handle keeps it from being replaced.

        A missing file is never locked (it can simply be created). Any other open
        failure (sharing violation, access denied) counts as locked, because the later
        replace would fail the same way.
        """
        handle = self._kernel32.CreateFileW(
            str(path), _DELETE_ACCESS, _NO_SHARING, None, _OPEN_EXISTING, 0, None
        )
        if handle == self._invalid:
            error = self._ctypes.get_last_error()
            return error not in {_ERROR_FILE_NOT_FOUND, _ERROR_PATH_NOT_FOUND}
        self._kernel32.CloseHandle(handle)
        return False


class NeverLockedProbe:
    """`ExportTargetLockProbe` for systems where replacing an open file works."""

    def is_locked(self, path: Path) -> bool:
        """Always False: POSIX ``rename`` replaces files that are still open."""
        return False


def default_lock_probe():
    """The probe for the running OS (Windows: exclusive open, else: never locked)."""
    if sys.platform == "win32" and os.name == "nt":
        return WindowsExclusiveOpenProbe()
    return NeverLockedProbe()
