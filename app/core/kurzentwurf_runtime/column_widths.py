from __future__ import annotations

import re

DEFAULT_COLUMN_WEIGHTS: tuple[float, float, float, float] = (10.0, 20.0, 60.0, 10.0)
DEFAULT_COLUMN_WEIGHTS_TEXT = "10 20 60 10"


def parse_column_weights(raw_text: str | None) -> tuple[float, float, float, float]:
    """Parse a four-number weighted column string like '10 20 60 10'."""

    text = str(raw_text or "").strip()
    if not text:
        return DEFAULT_COLUMN_WEIGHTS

    tokens = [part for part in re.split(r"[\s,;]+", text) if part]
    if len(tokens) != 4:
        raise ValueError(
            "Spaltengewichte muessen aus genau vier Zahlen bestehen (z. B. 10 20 60 10)."
        )

    values: list[float] = []
    for token in tokens:
        try:
            value = float(token)
        except Exception as exc:
            raise ValueError(f"Ungueltige Zahl in Spaltengewichten: '{token}'.") from exc
        if value <= 0:
            raise ValueError("Spaltengewichte muessen groesser als 0 sein.")
        values.append(value)

    return (values[0], values[1], values[2], values[3])


def normalize_column_weights_text(raw_text: str | None) -> str:
    """Return a normalized, stable string representation for persisted settings."""

    values = parse_column_weights(raw_text)
    parts: list[str] = []
    for value in values:
        if float(value).is_integer():
            parts.append(str(int(value)))
        else:
            parts.append(f"{value:g}")
    return " ".join(parts)


def resolve_column_width_percentages(raw_text: str | None) -> tuple[float, float, float, float]:
    """Resolve weighted column sizes to percentages summing up to 100."""

    try:
        weights = parse_column_weights(raw_text)
    except ValueError:
        weights = DEFAULT_COLUMN_WEIGHTS

    total = sum(weights)
    if total <= 0:
        weights = DEFAULT_COLUMN_WEIGHTS
        total = sum(weights)

    return tuple((weight / total) * 100.0 for weight in weights)
