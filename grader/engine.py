"""Judges one level: your tests, the technique, the monsters and your quest log."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

from grader import questlog, seal
from grader.model import Check, Context, Level, LevelResult, Mutant
from grader.mutants import MutantError, summoned
from grader.runner import failure_excerpt, run_pytest

WORKERS = min(4, max(2, os.cpu_count() or 2))


def check_level(level: Level) -> LevelResult:
    result = LevelResult(level, monsters=len(level.mutants))
    add = result.checks.append

    # 1. The rule of the dungeon: testers don't change the code under test.
    tampered = seal.verify(("src",))
    if tampered:
        add(Check(False, "The dungeon is untouched",
                  "You changed code under src/ (" + ", ".join(tampered) + "). You are the tester: "
                  "the dungeon is correct, so change your tests instead. "
                  "Undo it with:  git checkout -- src"))
        return result
    add(Check(True, "The dungeon is untouched"))

    # 2. Run the student's tests against the real dungeon.
    if not level.path.exists():
        add(Check(False, "Write your first test", f"The folder {level.folder} is missing."))
        return result
    real = run_pytest([level.folder, *level.pytest_args], probe=True)
    probe = real.probe or {"items": [], "results": {}}
    items = probe["items"]

    if real.returncode == 5 or (real.returncode == 0 and not items):
        add(Check(False, "Write your first test",
                  f"pytest found no tests in {level.folder}. Test files must be called test_*.py "
                  "and test functions must start with test_."))
        add(quest_log(level))
        return result
    if real.returncode in (2, 3, 4) or probe.get("collect_errors") or real.timed_out:
        add(Check(False, "Your test files load without errors", failure_excerpt(real.output)))
        add(quest_log(level))
        return result

    add(Check(len(items) >= level.min_tests, f"Found {len(items)} test(s)",
              "" if len(items) >= level.min_tests else f"This level needs at least {level.min_tests}."))

    passed = real.returncode == 0
    add(Check(passed, "Your tests pass against the real dungeon",
              "" if passed else
              "The dungeon is correct, so a failing test means the TEST is wrong. "
              "Read what pytest says:\n" + failure_excerpt(real.output)))

    # 3. Technique checks.
    def run(*args: str, probe: bool = False, env: dict[str, str] | None = None):
        return run_pytest([level.folder, *level.pytest_args, *args], probe=probe, env=env)

    ctx = Context(level, probe, run)
    for technique in level.checks:
        outcome = technique(ctx)
        result.checks.extend([outcome] if isinstance(outcome, Check) else outcome)

    # 4. Release the monsters (only worth it once the tests pass).
    if level.mutants:
        if passed:
            with ThreadPoolExecutor(WORKERS) as pool:
                fights = list(pool.map(lambda m: _fight(level, m), level.mutants))
            result.checks.extend(fights)
            result.slain = sum(1 for c in fights if c.ok and not c.skipped)
        else:
            add(Check(False, f"{len(level.mutants)} monster(s) waiting",
                      "The monsters come out once your tests pass against the real dungeon."))

    # 5. The quest log.
    add(quest_log(level))
    return result


def _fight(level: Level, mutant: Mutant) -> Check:
    if mutant.posix_only and os.name == "nt":
        return Check(True, f"Not fought on Windows: {mutant.name}",
                     "This monster only appears on Linux/macOS. CI will fight it.", skipped=True)
    try:
        with summoned(mutant) as src:
            run = run_pytest([level.folder, "-x", "-q", *level.pytest_args], src=src, timeout=180)
    except MutantError as exc:
        return Check(False, f"Monster could not be summoned: {mutant.name}", str(exc))
    if run.returncode in (1, 2) or run.timed_out:
        return Check(True, f"Slain: {mutant.name}")
    if run.returncode == 0:
        return Check(False, f"Survived: {mutant.name}", mutant.hint)
    return Check(False, f"Monster fight went wrong: {mutant.name}",
                 f"pytest exited with code {run.returncode}:\n" + failure_excerpt(run.output))


def quest_log(level: Level) -> Check:
    title = "Quest log: your commits explain what you did and why"
    mine = questlog.for_folder(level.folder)
    if mine is None:
        return Check(True, title, "There is no git history here to read. CI will check your quest log.",
                     skipped=True)
    bad = [entry for entry in mine if not entry.ok]
    if bad:
        return Check(False, title, "\n".join(questlog.describe_problems(e) for e in bad)
                     + "\n" + questlog.FIX_HINT)
    if questlog.uncommitted(level.folder):
        return Check(False, title,
                     f"You have changes in {level.folder} that aren't committed yet. Commit them:  "
                     f"git add {level.folder}  then  git commit  (fill in the quest log template).")
    if not mine:
        return Check(False, title,
                     f"No commit with your {level.tag} work yet. Commit it:  git add {level.folder}  "
                     "then  git commit  (fill in the quest log template).")
    return Check(True, f"Quest log: {len(mine)} entr{'y' if len(mine) == 1 else 'ies'} for this level")
