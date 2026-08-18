"""Seeds a pristine temp project root per acceptance run."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def acceptance_project_root(tmp_path: Path) -> Path:
    """A fresh, empty temp directory — the acceptance suite's project root for one run."""
    return tmp_path
