"""The Final Boss: the Hydra.

Clearing the levels shows your tests work one level at a time. The boss checks
the whole suite the way a real CI pipeline does. Each phase is something real
projects run on every push.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from grader import ROOT, questlog, seal
from grader.engine import check_level
from grader.levels import LEVELS
from grader.model import Check, LevelResult
from grader.runner import failure_excerpt, run_pytest

# The ten levels on their own reach about 92%. The last stretch is the boss's job:
# find the dungeon code no level asked about, and test it.
COVERAGE_MINIMUM = 98.0
SWARM_WORKERS = "4"


def _seeds() -> list[int]:
    sha = os.environ.get("GITHUB_SHA", "")
    if not sha:
        try:
            sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                 text=True).stdout.strip()
        except FileNotFoundError:
            sha = ""
    per_commit = int(sha[:6], 16) % 100_000 if sha else 7
    return [1, 42, per_commit]


def fight(on_level: Callable[[LevelResult], None] | None = None) -> tuple[list[LevelResult], list[Check]]:
    levels = []
    for level in LEVELS:
        outcome = check_level(level)
        levels.append(outcome)
        if on_level:
            on_level(outcome)

    phases: list[Check] = []

    uncleared = [r.level.label for r in levels if not r.cleared]
    phases.append(Check(not uncleared, "The Gauntlet: every level is cleared",
                        "Not cleared yet: " + ", ".join(uncleared) if uncleared else ""))

    problems = seal.verify()
    phases.append(Check(not problems, "The Seal: src/, grader/ and .github/ are untouched",
                        "\n".join(problems)))

    base = run_pytest(["tests", "-q"])
    if base.returncode != 0:
        broken = ("Your whole test suite (`pytest tests`) doesn't pass in normal order yet:\n"
                  + failure_excerpt(base.output))
        for title in ("The Shuffle", "The Swarm", "The Purity Trial"):
            phases.append(Check(False, f"{title}: waiting for a passing suite", broken))
    else:
        phases.append(_shuffle())
        phases.append(_swarm())
        phases.append(_purity())

    phases.append(_aura())
    phases.append(_chronicle())
    return levels, phases


def _shuffle() -> Check:
    title = "The Shuffle: the suite passes in random order"
    for seed in _seeds():
        run = run_pytest(["tests", "-q", "--random-order-bucket=global", f"--random-order-seed={seed}"])
        if run.returncode != 0:
            return Check(False, title,
                         f"Your tests pass in normal order but FAIL with random seed {seed}, so some "
                         "test depends on another test running first (shared state). Reproduce it:\n"
                         f"  pytest tests --random-order-bucket=global --random-order-seed={seed}\n"
                         + failure_excerpt(run.output))
    return Check(True, title)


def _swarm() -> Check:
    run = run_pytest(["tests", "-q", "-n", SWARM_WORKERS])
    return Check(run.returncode == 0, f"The Swarm: the suite passes on {SWARM_WORKERS} parallel workers",
                 "" if run.returncode == 0 else
                 "Tests that pass alone but fail in parallel usually share a file, a folder or "
                 "an environment variable. Use tmp_path and monkeypatch. Reproduce: pytest tests -n 4\n"
                 + failure_excerpt(run.output))


def _purity() -> Check:
    run = run_pytest(["tests", "-q", "-W", "error", "--strict-markers", "--strict-config"])
    return Check(run.returncode == 0, "The Purity Trial: no warnings, no unknown markers",
                 "" if run.returncode == 0 else
                 "With -W error every warning becomes a failure. Catch expected warnings with "
                 "pytest.warns. Reproduce: pytest tests -W error --strict-markers\n"
                 + failure_excerpt(run.output))


def _aura() -> Check:
    title = f"The Aura: {COVERAGE_MINIMUM:g}% branch coverage of the whole dungeon"
    with tempfile.TemporaryDirectory(prefix="pytest-quest-cov-") as tmp:
        report = Path(tmp) / "coverage.json"
        run_pytest(["tests", "-q", "--cov=src/dungeon", "--cov-branch",
                    f"--cov-report=json:{report}", "--cov-report="],
                   env={"COVERAGE_FILE": str(Path(tmp) / ".coverage")})
        if not report.exists():
            return Check(False, title, "Coverage could not be measured.")
        data = json.loads(report.read_text(encoding="utf-8"))
    total = data["totals"]["percent_covered"]
    if total + 1e-9 >= COVERAGE_MINIMUM:
        return Check(True, f"{title} (you have {total:.1f}%)")
    weakest = sorted((v["summary"]["percent_covered"], Path(k).name) for k, v in data["files"].items())
    listing = ", ".join(f"{name} {pct:.0f}%" for pct, name in weakest if pct < 100)
    return Check(False, title,
                 f"You're at {total:.1f}%. Least covered: {listing}. Here be dragons: some dungeon "
                 "code isn't part of any level. Find it and test it (tag those commits 'boss:'). "
                 "See the map yourself:\n"
                 "  pytest tests --cov=src/dungeon --cov-branch --cov-report=term-missing")


def _chronicle() -> Check:
    title = "The Chronicle: every commit to tests/ has a quest log entry"
    entries = questlog.entries()
    if entries is None:
        return Check(True, title, "No git history here. CI will read your chronicle.", skipped=True)
    bad = [e for e in entries if not e.ok]
    return Check(not bad, title,
                 "\n".join(questlog.describe_problems(e) for e in bad) + "\n" + questlog.FIX_HINT
                 if bad else "")


def defeated(phases: list[Check]) -> bool:
    return all(p.ok or p.skipped for p in phases)
