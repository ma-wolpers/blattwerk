"""Sicheres Auswerten und Sampling von Funktionsgraph-Ausdrücken (`expr`).

Bewusst als eigenständiges, in sich geschlossenes Modul: Der hier verwendete
`ast`-basierte Safe-Evaluator ist der einzige Ort im Rendering-Pfad, der
Nutzer-Eingaben (die Term-Zeichenkette aus `functions[].expr`) tatsächlich
als Code interpretiert. Ein eigenes Modul erleichtert spätere
Sicherheits-Audits, da der komplette Angriffsflächen-relevante Code an
einer Stelle liegt statt verteilt in einer größeren Rendering-Datei.
"""

from __future__ import annotations

import ast
import math

from .answer_grid_entries import _inside_grid


def _sample_function_points(expr, x_min, x_max, origin, step_x, step_y, cols, rows):
    """Samplet einen Funktionsgraphen und bildet die Punkte auf Grid-Koordinaten ab.

    Die Sample-Anzahl skaliert mit der Breite des Definitionsbereichs
    (min. 24, max. 360), damit sowohl kurze als auch weite Intervalle eine
    glatte Kurve ergeben, ohne bei extremen Domains unbegrenzt viele Punkte
    zu erzeugen. Punkte mit `NaN`/`Inf`-Ergebnis (z. B. bei Polstellen) oder
    außerhalb des sichtbaren Rasters werden übersprungen statt die Kurve
    abzubrechen.
    """
    if origin is None:
        return []

    sample_count = max(24, min(360, int((x_max - x_min) * 24)))
    points = []
    for index in range(sample_count + 1):
        x_value = x_min + ((x_max - x_min) * index / sample_count)
        y_value = _eval_function_expr(expr, x_value)
        if y_value is None or math.isnan(y_value) or math.isinf(y_value):
            continue

        gx = origin[0] + (x_value / step_x)
        gy = origin[1] - (y_value / step_y)
        if _inside_grid(gx, gy, cols, rows):
            points.append((gx, gy))

    return points


def _eval_function_expr(expr, x_value):
    """Wertet einen mathematischen Ausdruck mit Variable `x` sicher aus.

    `^` wird vorab zu `**` normalisiert (gängige Nutzererwartung aus
    Taschenrechner-/Mathematik-Notation). Die eigentliche Auswertung läuft
    über ein von `_is_safe_expression_tree` geprüftes AST mit einer engen
    Whitelist an Namen/Funktionen (`sin`, `cos`, ... ) statt über ein
    ungefiltertes `eval` auf dem Rohtext — siehe `_is_safe_expression_tree`
    für die genaue Sicherheitsgrenze. Jeder Fehler (Syntax, Laufzeit,
    Division durch Null) liefert `None` statt eine Exception zu propagieren,
    da ein einzelner ungültiger Ausdruck nicht das gesamte Dokument-Rendering
    abbrechen soll.
    """
    normalized_expr = (expr or "").replace("^", "**")
    safe_globals = {
        "__builtins__": {},
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "sqrt": math.sqrt,
        "log": math.log,
        "exp": math.exp,
        "abs": abs,
        "pi": math.pi,
        "e": math.e,
    }

    try:
        tree = ast.parse(normalized_expr, mode="eval")
    except SyntaxError:
        return None

    if not _is_safe_expression_tree(tree):
        return None

    try:
        return float(
            eval(compile(tree, "<grid-function>", "eval"), safe_globals, {"x": x_value})
        )
    except Exception:
        return None


def _is_safe_expression_tree(tree):
    """Validiert AST-Knoten für eine sichere mathematische Auswertung.

    Erlaubt ausschließlich arithmetische Operatoren, Konstanten, den Namen
    `x` sowie Aufrufe der in `allowed_names` gelisteten Mathe-Funktionen.
    Jeder andere Knotentyp (Attributzugriff, Subscripts, Comprehensions,
    Lambdas, Imports, ...) führt zur Ablehnung — das ist die eigentliche
    Sicherheitsgrenze, die verhindert, dass ein `expr`-Wert beliebigen
    Python-Code ausführen kann.
    """
    allowed_nodes = {
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Name,
        ast.Load,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.Mod,
        ast.USub,
        ast.UAdd,
        ast.Call,
    }
    allowed_names = {"x", "sin", "cos", "tan", "sqrt", "log", "exp", "abs", "pi", "e"}

    for node in ast.walk(tree):
        if type(node) not in allowed_nodes:
            return False
        if isinstance(node, ast.Name) and node.id not in allowed_names:
            return False
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                return False
            if node.func.id not in allowed_names:
                return False
    return True
