"""Technique checks: did you use the pytest feature the level is about?

Monsters check that your tests WORK. These checks look at HOW you wrote them,
for the skills a monster can't test on its own (fixtures, parametrize, marks...).
"""

from __future__ import annotations

import ast
import json
import tempfile
from collections import Counter
from pathlib import Path

from grader import ROOT
from grader.model import Check, CheckResult, Context


def _used_fixtures(ctx: Context) -> set[str]:
    used: set[str] = set()
    for item in ctx.items:
        used.update(item["fixtures"])
    return used


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _trees(ctx: Context) -> list[ast.Module]:
    trees = []
    for path in sorted(ctx.test_dir.rglob("*.py")):
        try:
            trees.append(ast.parse(path.read_text(encoding="utf-8")))
        except SyntaxError:
            pass  # pytest already reported it
    return trees


# ------------------------------------------------------------ level 04


def parametrized(minimum: int):
    def check(ctx: Context) -> CheckResult:
        counts = Counter(item["test"] for item in ctx.items if item["parametrized"])
        best = max(counts.values(), default=0)
        return Check(
            best >= minimum,
            f"One test function parametrized with {minimum}+ cases",
            "" if best >= minimum else
            f"Your biggest parametrized test has {best} case(s). Use @pytest.mark.parametrize "
            f"to run ONE test function over a table of {minimum} or more cases.",
        )
    return check


# ------------------------------------------------------------ level 05


def _fixture_definitions(path: Path) -> dict[str, list[str]]:
    """{fixture name: [names of its arguments]} for every @pytest.fixture in a file."""
    def is_fixture(decorator: ast.expr) -> bool:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        return (isinstance(target, ast.Attribute) and target.attr == "fixture") or (
            isinstance(target, ast.Name) and target.id == "fixture"
        )

    def fixture_name(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                for keyword in decorator.keywords:
                    if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                        return str(keyword.value.value)
        return node.name

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return {}
    found = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
            is_fixture(d) for d in node.decorator_list
        ):
            found[fixture_name(node)] = [a.arg for a in node.args.args + node.args.kwonlyargs]
    return found


def conftest_fixtures(minimum: int = 2):
    def check(ctx: Context) -> CheckResult:
        conftest = ctx.test_dir / "conftest.py"
        title = f"{minimum}+ fixtures defined in {_rel(conftest)}"
        if not conftest.exists():
            return Check(False, title, f"Create {_rel(conftest)} and define your fixtures there.")
        defined = _fixture_definitions(conftest)
        chained = sorted(name for name, args in defined.items() if any(a in defined for a in args))
        used = sorted(_used_fixtures(ctx) & defined.keys())
        return [
            Check(len(defined) >= minimum, title,
                  "" if len(defined) >= minimum else
                  f"Found {len(defined)}: {', '.join(defined) or 'none'}. A fixture is a function "
                  "decorated with @pytest.fixture."),
            Check(bool(chained), "A fixture that builds on another fixture",
                  "" if chained else
                  "Let one fixture ask for another one as an argument, e.g. a `rich_hero` "
                  "fixture that takes `hero` and gives it gold."),
            Check(len(used) >= minimum, f"Your tests use {minimum}+ of those fixtures",
                  "" if len(used) >= minimum else
                  f"Tests use: {', '.join(used) or 'none'}. Ask for a fixture by adding its name "
                  "as an argument of the test function."),
        ]
    return check


# ------------------------------------------------------------ level 06


def uses_fixtures(*names: str):
    def check(ctx: Context) -> CheckResult:
        used = _used_fixtures(ctx)
        return [
            Check(name in used, f"Uses the built-in `{name}` fixture",
                  "" if name in used else f"No test asks for `{name}` yet.")
            for name in names
        ]
    return check


# ------------------------------------------------------------ level 07


def _has_marker(item: dict, name: str) -> bool:
    return any(m["name"] == name for m in item["markers"])


def registered_marker(name: str):
    def check(ctx: Context) -> CheckResult:
        registered = any(line.split(":")[0].split("(")[0].strip() == name
                         for line in ctx.probe.get("markers", []))
        return Check(registered, f"The custom `{name}` marker is registered",
                     "" if registered else
                     f"Register it in tests/conftest.py with a pytest_configure hook "
                     f"(see the level README). The grader runs this level with --strict-markers.")
    return check


def marker_used(name: str):
    def check(ctx: Context) -> CheckResult:
        marked = [i for i in ctx.items if _has_marker(i, name)]
        return Check(bool(marked), f"At least one test is marked `{name}`",
                     "" if marked else f"Put @pytest.mark.{name} on the tests that are slow.")
    return check


def fast_without(marker: str, limit: float = 1.0):
    def check(ctx: Context) -> CheckResult:
        title = f"`pytest -m \"not {marker}\"` runs fast (every test under {limit:g}s)"
        result = ctx.run("-m", f"not {marker}", probe=True)
        if result.returncode == 5:
            return Check(False, title, f"Every test is marked {marker}, so nothing is left to run. "
                                       "Only the slow ones should be marked.")
        if result.returncode != 0 or not result.probe:
            return Check(False, title, f"The run without {marker} tests failed.")
        if result.probe["deselected"] == 0:
            return Check(False, title, f"No test was deselected: mark the slow ones with @pytest.mark.{marker}.")
        slow = sorted(((r["duration"], nodeid) for nodeid, r in result.probe["results"].items()
                       if r["duration"] >= limit), reverse=True)
        if slow:
            listing = ", ".join(f"{nodeid.split('::')[-1]} ({secs:.1f}s)" for secs, nodeid in slow)
            return Check(False, title, f"These tests are slow but not marked {marker}: {listing}")
        return Check(True, title)
    return check


def skipif_with_reason(ctx: Context) -> CheckResult:
    found = [i for i in ctx.items
             if any(m["name"] == "skipif" and m["kwargs"].get("reason") for m in i["markers"])]
    return Check(bool(found), "A test with @pytest.mark.skipif(..., reason=...)",
                 "" if found else "Skip the platform-specific portal test where it can't work, "
                                  "and give a reason.")


def strict_xfail(ctx: Context) -> CheckResult:
    strict = [i for i in ctx.items
              if any(m["name"] == "xfail" and m["kwargs"].get("strict") is True for m in i["markers"])]
    xfailed = [i for i in strict if ctx.results.get(i["nodeid"], {}).get("outcome") == "xfailed"]
    title = "A strict xfail test that really fails (bug #13)"
    if not strict:
        return Check(False, title, "Mark the test for the known bug with @pytest.mark.xfail(strict=True, reason=...).")
    if not xfailed:
        return Check(False, title, "Your strict xfail test doesn't fail. It should prove the bug is still there.")
    return Check(True, title)


# ------------------------------------------------------------ level 08


def uses_test_doubles(ctx: Context) -> CheckResult:
    ok = bool(_used_fixtures(ctx) & {"mocker", "monkeypatch"})
    if not ok:
        for tree in _trees(ctx):
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("unittest"):
                    ok = ok or node.module == "unittest.mock" or any(a.name == "mock" for a in node.names)
                elif isinstance(node, ast.Import):
                    ok = ok or any(a.name.startswith("unittest.mock") for a in node.names)
    return Check(ok, "Uses test doubles (unittest.mock, mocker or monkeypatch)",
                 "" if ok else "Replace urlopen with a mock instead of calling the network.")


# ------------------------------------------------------------ level 09


def _ranges(numbers: list[int]) -> str:
    numbers = sorted(numbers)
    parts, start = [], None
    for i, n in enumerate(numbers):
        if start is None:
            start = n
        if i + 1 == len(numbers) or numbers[i + 1] != n + 1:
            parts.append(str(start) if start == n else f"{start}-{n}")
            start = None
    return ", ".join(parts)


def coverage(module: str, minimum: float):
    def check(ctx: Context) -> CheckResult:
        title = f"Branch coverage of src/dungeon/{module} is {minimum:g}%"
        with tempfile.TemporaryDirectory(prefix="pytest-quest-cov-") as tmp:
            report = Path(tmp) / "coverage.json"
            ctx.run("--cov=src/dungeon", "--cov-branch", f"--cov-report=json:{report}",
                    "--cov-report=", env={"COVERAGE_FILE": str(Path(tmp) / ".coverage")})
            if not report.exists():
                return Check(False, title, "Coverage could not be measured. Do your tests pass?")
            data = json.loads(report.read_text(encoding="utf-8"))
        entry = next((v for k, v in data.get("files", {}).items()
                      if k.replace("\\", "/").endswith(f"dungeon/{module}")), None)
        if entry is None:
            return Check(False, title, f"Your tests never import dungeon.{module.removesuffix('.py')}.")
        percent = entry["summary"]["percent_covered"]
        if percent + 1e-9 >= minimum:
            return Check(True, title)
        missing = []
        if entry.get("missing_lines"):
            missing.append(f"lines never run: {_ranges(entry['missing_lines'])}")
        if entry.get("missing_branches"):
            branches = ", ".join(f"{a}->{'exit' if b < 0 else b}" for a, b in entry["missing_branches"])
            missing.append(f"branches never taken: {branches}")
        return Check(False, title, f"You're at {percent:.1f}%. " + "; ".join(missing) +
                     f". See it yourself: pytest {ctx.level.folder} --cov=src/dungeon --cov-branch "
                     "--cov-report=term-missing")
    return check
