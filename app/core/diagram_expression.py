"""Ausdrucksparser für `:::termtree` und `:::logicgates` (Präzedenzklettern, ohne `eval`).

Welche Operatoren gelten, legt der Aufrufer in einer Tabelle fest. Beide Blöcke teilen
sich damit Klammern, Vorrang und Fehlerbehandlung.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


class ExpressionError(ValueError):
    """Der Ausdruck ist nicht wohlgeformt; die Meldung ist für Lehrkräfte formuliert."""


@dataclass(frozen=True)
class Expr:
    """Ausdrucksknoten: Blatt mit `children == ()`, sonst Operator `value` und seine Operanden."""

    value: str
    children: tuple = ()

    @property
    def is_leaf(self) -> bool:
        """Blatt: Zahl oder Variable."""
        return not self.children


@dataclass(frozen=True)
class Grammar:
    """Operatoren einer Ausdruckssprache.

    Attributes:
        levels: Binäre Operatoren je Vorrangstufe, schwächste zuerst: `(operatoren, rechtsassoziativ)`.
        prefix: Einstellige Operatoren davor.
        aliases: Schreibvarianten auf ihren Hauptnamen, z. B. `:` auf `/`.
        atom: Regex für ein Blatt.
    """

    levels: tuple[tuple[tuple[str, ...], bool], ...]
    prefix: tuple[str, ...]
    aliases: dict[str, str]
    atom: str


def _tokens(text: str, grammar: Grammar) -> list[str]:
    """Zerlegt den Text; Wortoperatoren dürfen nicht in Namen hineinschneiden."""
    words = [op for ops, _right in grammar.levels for op in ops] + list(grammar.prefix) + list(grammar.aliases)
    symbols = sorted({re.escape(word) for word in words if not word.isalpha()}, key=len, reverse=True)
    pattern = re.compile("|".join([grammar.atom, r"[()]"] + symbols))
    tokens: list[str] = []
    position = 0
    while position < len(text):
        if text[position].isspace():
            position += 1
            continue
        match = pattern.match(text, position)
        if not match or not match.group(0):
            raise ExpressionError(f"Unerwartetes Zeichen `{text[position]}`.")
        tokens.append(grammar.aliases.get(match.group(0).lower(), match.group(0)))
        position = match.end()
    return tokens


class _Parser:
    """Präzedenzklettern über die Token."""

    def __init__(self, tokens: list[str], grammar: Grammar):
        """Merkt sich Token und Grammatik."""
        self.tokens = tokens
        self.grammar = grammar
        self.pos = 0

    def peek(self) -> str | None:
        """Nächstes Token oder `None`."""
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _normalized(self) -> str | None:
        """Nächstes Token in Kleinschreibung (für Wortoperatoren)."""
        token = self.peek()
        return token.lower() if token is not None else None

    def binary(self, level: int) -> Expr:
        """Liest Stufe `level` und alles, was stärker bindet."""
        if level == len(self.grammar.levels):
            return self.prefix()
        operators, right = self.grammar.levels[level]
        left = self.binary(level + 1)
        while self._normalized() in operators:
            operator = self._normalized()
            self.pos += 1
            other = self.binary(level if right else level + 1)
            left = Expr(operator, (left, other))
        return left

    def prefix(self) -> Expr:
        """Einstelliger Operator oder Atom."""
        if self._normalized() in self.grammar.prefix:
            operator = self._normalized()
            self.pos += 1
            return Expr(operator, (self.prefix(),))
        return self.atom()

    def atom(self) -> Expr:
        """Klammerausdruck oder Blatt."""
        token = self.peek()
        if token is None:
            raise ExpressionError("Der Ausdruck endet zu früh.")
        self.pos += 1
        if token == "(":
            inner = self.binary(0)
            if self.peek() != ")":
                raise ExpressionError("Es fehlt eine schließende Klammer.")
            self.pos += 1
            return inner
        if token == ")" or token.lower() in {op for ops, _right in self.grammar.levels for op in ops}:
            raise ExpressionError(f"An dieser Stelle passt `{token}` nicht.")
        return Expr(token)


def parse_expression(text: str, grammar: Grammar) -> Expr:
    """Parst einen Ausdruck.

    Args:
        text: Ausdruck, z. B. `(3+4)*2`.
        grammar: Operatoren der Sprache.

    Returns:
        Wurzel des Ausdrucksbaums.

    Raises:
        ExpressionError: bei falscher Klammerung oder unerwarteten Zeichen.
    """
    parser = _Parser(_tokens(text, grammar), grammar)
    result = parser.binary(0)
    if parser.peek() is not None:
        raise ExpressionError(f"Unerwartetes `{parser.peek()}` am Ende.")
    return result
