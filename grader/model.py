"""The data the grader works with."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union

from grader import ROOT


@dataclass(frozen=True)
class Mutant:
    """A monster: a copy of the dungeon with one small bug planted in it.

    The grader copies src/, replaces `find` (which must appear exactly once in
    `file`) with `replace`, and runs the student's tests against that copy.
    If the tests fail, the monster is slain.
    """

    name: str
    file: str  # path inside src/dungeon/, e.g. "hero.py"
    find: str
    replace: str
    hint: str
    posix_only: bool = False  # can only be detected on Linux/macOS


@dataclass
class Check:
    ok: bool
    title: str
    detail: str = ""
    skipped: bool = False  # not decided here (e.g. needs CI); doesn't block the level


CheckResult = Union[Check, Sequence[Check]]


@dataclass(frozen=True)
class Level:
    number: int
    title: str
    skill: str
    xp: int
    mutants: tuple[Mutant, ...] = ()
    checks: tuple[Callable[[Context], CheckResult], ...] = ()
    pytest_args: tuple[str, ...] = ()
    min_tests: int = 1

    @property
    def tag(self) -> str:
        return f"level-{self.number:02d}"

    @property
    def folder(self) -> str:
        return f"tests/level_{self.number:02d}"

    @property
    def path(self) -> Path:
        return ROOT / self.folder

    @property
    def label(self) -> str:
        return f"Level {self.number:02d} · {self.title}"


@dataclass
class Context:
    """What a technique check gets to look at."""

    level: Level
    probe: dict[str, Any]
    run: Callable[..., Any]  # run(*extra_pytest_args, probe=False) -> RunResult

    @property
    def items(self) -> list[dict[str, Any]]:
        return self.probe.get("items", [])

    @property
    def results(self) -> dict[str, dict[str, Any]]:
        return self.probe.get("results", {})

    @property
    def test_dir(self) -> Path:
        return self.level.path


@dataclass
class LevelResult:
    level: Level
    checks: list[Check] = field(default_factory=list)
    monsters: int = 0
    slain: int = 0

    @property
    def cleared(self) -> bool:
        return bool(self.checks) and all(c.ok or c.skipped for c in self.checks)

    @property
    def xp(self) -> int:
        return self.level.xp if self.cleared else 0

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if not c.ok and not c.skipped]
