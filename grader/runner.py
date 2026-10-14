"""Runs pytest in a subprocess so every run starts clean."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from grader import ROOT

TIMED_OUT = -9

# Options the grader always adds. They make runs repeatable and keep the
# student's own pytest settings (PYTEST_ADDOPTS, cache) out of the way.
BASE_ARGS = (
    "-p", "grader.plugins.no_network",
    "-p", "no:cacheprovider",
    "-p", "no:randomly",
    "--color=no",
)


@dataclass
class RunResult:
    returncode: int
    output: str
    probe: dict[str, Any] | None = None

    @property
    def timed_out(self) -> bool:
        return self.returncode == TIMED_OUT


def run_pytest(
    args: list[str] | tuple[str, ...],
    *,
    src: Path | None = None,
    probe: bool = False,
    env: dict[str, str] | None = None,
    timeout: int = 300,
) -> RunResult:
    """Run `python -m pytest <args>` from the repo root.

    src:   run against this copy of src/ instead of the real one (used for monsters)
    probe: also record what was collected and how each test ended (see plugins/probe.py)
    """
    child_env = os.environ.copy()
    child_env.pop("PYTEST_ADDOPTS", None)
    child_env["PYTHONDONTWRITEBYTECODE"] = "1"
    child_env["PYTHONIOENCODING"] = "utf-8"
    child_env.update(env or {})

    cmd = [sys.executable, "-m", "pytest", *BASE_ARGS, *args]
    if src is not None:
        cmd += ["-o", f"pythonpath={src}"]

    with tempfile.TemporaryDirectory(prefix="pytest-quest-") as tmp:
        probe_file = Path(tmp) / "probe.json"
        if probe:
            cmd += ["-p", "grader.plugins.probe"]
            child_env["GRADER_PROBE_OUT"] = str(probe_file)
        try:
            done = subprocess.run(
                cmd,
                cwd=ROOT,
                env=child_env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            output = exc.stdout if isinstance(exc.stdout, str) else ""
            return RunResult(TIMED_OUT, output + f"\n[timed out after {timeout}s]")
        data = None
        if probe and probe_file.exists():
            data = json.loads(probe_file.read_text(encoding="utf-8"))
        return RunResult(done.returncode, done.stdout + done.stderr, data)


def failure_excerpt(output: str, max_lines: int = 60) -> str:
    """The interesting part of pytest's output: the FAILURES/ERRORS section."""
    lines = output.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.startswith("=") and ("FAILURES" in line or "ERRORS" in line)),
        max(0, len(lines) - 30),
    )
    excerpt = lines[start:]
    if len(excerpt) > max_lines:
        excerpt = excerpt[: max_lines - 1] + [f"... ({len(excerpt) - max_lines + 1} more lines, run pytest yourself to see them)"]
    return "\n".join(excerpt)
