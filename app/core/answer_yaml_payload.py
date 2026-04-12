"""Shared YAML payload parsing for answer renderers."""

from __future__ import annotations

import yaml


def parse_yaml_answer_payload(content):
    """Parse answer YAML content and return a mapping payload or an empty dict."""

    text = (content or "").strip()
    if not text:
        return {}

    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError:
        return {}

    if isinstance(parsed, dict):
        return parsed
    return {}


def extract_solution_text(payload):
    """Extract explicit fallback solution text from payload keys."""

    if not isinstance(payload, dict):
        return ""
    return str(payload.get("solution") or payload.get("solution_text") or "")


def parse_yaml_answer_payload_with_solution(content):
    """Parse answer YAML and return `(payload, fallback_solution_text)`.

    Fallback solution text is read only from explicit payload keys
    `solution` or `solution_text`.
    """

    payload = parse_yaml_answer_payload(content)
    return payload, extract_solution_text(payload)
