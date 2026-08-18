"""SC-001/SC-002 acceptance walkthroughs — real, paid API calls. Never run by the default suite.

Run explicitly with: uv run pytest -m acceptance tests/acceptance/test_sc001_sc002.py
Requires ANTHROPIC_API_KEY in the repo-root .env.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.acceptance

SC001_PROMPT = (
    "create a console program in a file called log.py that asks for a number a and a base b "
    "and prints log base b of a"
)
SC002_FOLLOWUP = "also make it calculate a raised to the power b, and print that too"


def _run_agent(project_root: Path, prompts: list[str]) -> subprocess.CompletedProcess:
    transcript = "\n".join([*prompts, "suerte_socio\n"])
    return subprocess.run(
        [sys.executable, "-m", "cyborg_ant"],
        cwd=project_root,
        input=transcript,
        capture_output=True,
        text=True,
        timeout=300,
    )


def _latest_run_tool_calls(project_root: Path) -> list[str]:
    run_files = sorted((project_root / ".agent_runs").glob("*.jsonl"))
    records = (json.loads(line) for line in run_files[-1].read_text().splitlines() if line)
    return [r["name"] for r in records if r.get("event") == "tool_call"]


def test_sc001_agent_creates_a_working_program(acceptance_project_root: Path) -> None:
    _run_agent(acceptance_project_root, [SC001_PROMPT])

    log_py = acceptance_project_root / "log.py"
    assert log_py.exists(), "log.py was not created unattended"

    result = subprocess.run(
        [sys.executable, str(log_py)], input="8\n2\n", capture_output=True, text=True, timeout=10
    )
    assert "3" in result.stdout


def test_sc002_agent_reads_modifies_and_verifies(acceptance_project_root: Path) -> None:
    _run_agent(acceptance_project_root, [SC001_PROMPT, SC002_FOLLOWUP])

    tool_calls = _latest_run_tool_calls(acceptance_project_root)
    assert "read_file" in tool_calls
    assert "write_file" in tool_calls
    assert "run_bash" in tool_calls
    assert tool_calls.index("read_file") < tool_calls.index("write_file")
