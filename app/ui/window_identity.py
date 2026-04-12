"""Windows-spezifische Fensteridentität (Taskleiste + Icon) für Blattwerk."""

from __future__ import annotations

import sys
from pathlib import Path
import tkinter as tk

APP_USER_MODEL_ID = "7thCloud.Blattwerk.2026.03"


def _apply_taskbar_icon_winapi(window: tk.Misc, icon_path: Path) -> None:
    """Setzt das Fenster-Icon via WinAPI explizit fuer SMALL und BIG."""
    try:
        import ctypes

        window.update_idletasks()

        user32 = ctypes.windll.user32
        image_icon = 1
        lr_loadfromfile = 0x0010
        lr_defaultsize = 0x0040
        wm_seticon = 0x0080
        icon_small = 0
        icon_big = 1
        gclp_hicon = -14
        gclp_hiconsm = -34

        user32.LoadImageW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_wchar_p,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        user32.LoadImageW.restype = ctypes.c_void_p
        user32.SendMessageW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        user32.SendMessageW.restype = ctypes.c_void_p
        user32.SetClassLongPtrW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_void_p,
        ]
        user32.SetClassLongPtrW.restype = ctypes.c_void_p

        hwnd = ctypes.c_void_p(window.winfo_id())
        icon_small_handle = user32.LoadImageW(
            None,
            str(icon_path),
            image_icon,
            16,
            16,
            lr_loadfromfile,
        )
        icon_big_handle = user32.LoadImageW(
            None,
            str(icon_path),
            image_icon,
            0,
            0,
            lr_loadfromfile | lr_defaultsize,
        )

        if icon_small_handle:
            user32.SendMessageW(hwnd, wm_seticon, ctypes.c_void_p(icon_small), icon_small_handle)
        if icon_big_handle:
            user32.SendMessageW(hwnd, wm_seticon, ctypes.c_void_p(icon_big), icon_big_handle)

        if icon_big_handle:
            user32.SetClassLongPtrW(hwnd, gclp_hicon, icon_big_handle)
        if icon_small_handle:
            user32.SetClassLongPtrW(hwnd, gclp_hiconsm, icon_small_handle)
    except Exception:
        return


def configure_windows_process_identity() -> None:
    """Setzt eine eigene AppUserModelID für konsistente Taskleisten-Darstellung."""
    if not sys.platform.startswith("win"):
        return

    try:
        import ctypes

        shell32 = ctypes.windll.shell32
        shell32.SetCurrentProcessExplicitAppUserModelID.argtypes = [ctypes.c_wchar_p]
        shell32.SetCurrentProcessExplicitAppUserModelID.restype = ctypes.c_long
        shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        return


def apply_window_icon(window: tk.Misc) -> None:
    """Wendet das Projekt-Icon auf ein Tk-Fenster an, falls vorhanden."""
    if not sys.platform.startswith("win"):
        return

    icon_path = Path(__file__).resolve().parents[2] / "assets" / "app.ico"
    if not icon_path.exists():
        return

    try:
        window.iconbitmap(default=str(icon_path))
    except tk.TclError:
        return

    _apply_taskbar_icon_winapi(window, icon_path)
