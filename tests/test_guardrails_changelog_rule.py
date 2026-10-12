"""Changelog rule of the AI guardrails (`tools/ci/guardrails_process.py`).

CHANGELOG.md is user-facing only: app/library changes need an entry unless the staged
DEVELOPMENT_LOG entry marks them as internal; tooling/governance never needs one.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "ci"))

from guardrails_process import _check_changelog_updated  # noqa: E402


def _errors(staged, dev_log_lines=None):
    errors: list[str] = []
    _check_changelog_updated(set(staged), errors, dev_log_lines)
    return errors


def test_app_change_without_changelog_fails():
    """A staged app change needs a changelog entry."""
    assert _errors({"app/core/x.py"})


def test_app_change_with_changelog_passes():
    """Staging CHANGELOG.md satisfies the rule."""
    assert not _errors({"app/ui/y.py", "CHANGELOG.md"})


def test_internal_app_change_with_opt_out_marker_passes():
    """A staged dev-log line with the marker exempts purely internal changes."""
    lines = ["- **Refactor.** Ausgabe unveraendert. Kein CHANGELOG-Eintrag (rein intern)."]
    assert not _errors({"app/core/x.py", "docs/intern/DEVELOPMENT_LOG.md"}, lines)


def test_marker_must_be_in_added_lines():
    """An unrelated added dev-log line does not exempt the change."""
    assert _errors({"bw_libs/a.py", "docs/intern/DEVELOPMENT_LOG.md"}, ["- Feature X."])


def test_tooling_and_governance_need_no_changelog():
    """tools/, AGENTS.md and workflows are not user-facing."""
    staged = {"tools/ci/check_ai_guardrails.py", "AGENTS.md", ".github/workflows/quality-guardrails.yml"}
    assert not _errors(staged)


def test_nothing_staged_passes():
    """CI (nothing staged) is never blocked by this rule."""
    assert not _errors(set())
