"""Tastatur-Diagnose: zeigt exakt welche keysym/state-Kombination jede Taste erzeugt.

Starten mit:  .venv/Scripts/python.exe tools/key_diagnostic.py

Dann einfach die gewünschten Tastenkombinationen drücken.
ESC oder Fenster schließen zum Beenden.
"""
import tkinter as tk

root = tk.Tk()
root.title("Blattwerk Key Diagnostic — Tasten drücken, ESC zum Beenden")
root.geometry("700x420")

label = tk.Label(root, text="Drücke eine Tastenkombination…", font=("Courier", 13))
label.pack(pady=10)

log_text = tk.Text(root, font=("Courier", 11), height=20, state="disabled")
log_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))

def log(msg):
    log_text.config(state="normal")
    log_text.insert("end", msg + "\n")
    log_text.see("end")
    log_text.config(state="disabled")

def on_key(event):
    modifiers = []
    s = int(event.state)
    if s & 0x0001: modifiers.append("Shift")
    if s & 0x0002: modifiers.append("Lock")
    if s & 0x0004: modifiers.append("Control")
    if s & 0x0008: modifiers.append("Mod1/Alt")
    if s & 0x0010: modifiers.append("Mod2")
    if s & 0x0020: modifiers.append("Mod3")
    if s & 0x0040: modifiers.append("Mod4")
    if s & 0x0080: modifiers.append("Mod5")
    if s & 0x20000: modifiers.append("AltGr/ExtendedAlt")

    mod_str = "+".join(modifiers) if modifiers else "(keine)"
    msg = (
        f"keysym={event.keysym!r:20s}  keycode={event.keycode:3d}  "
        f"state={s:#010x}  char={event.char!r:6s}  modifiers=[{mod_str}]"
    )
    log(msg)
    label.config(text=f"Letzte Taste: keysym={event.keysym!r}, state={s:#010x}")

    if event.keysym == "Escape":
        root.destroy()

root.bind("<KeyPress>", on_key)
root.focus_set()

log("Bereit. Drücke verschiedene Kombinationen wie Strg+Alt+C, Strg+Shift+C, etc.")
log("-" * 80)

root.mainloop()
