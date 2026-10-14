"""Summons monsters: temporary copies of the dungeon with one bug planted."""

from __future__ import annotations

import py_compile
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from grader import ROOT
from grader.model import Mutant


class MutantError(Exception):
    """The monster can't be summoned (its `find` text isn't in the dungeon exactly once)."""


def apply(mutant: Mutant, source: str) -> str:
    source = source.replace("\r\n", "\n")
    found = source.count(mutant.find)
    if found != 1:
        raise MutantError(
            f"monster {mutant.name!r}: expected its code exactly once in "
            f"src/dungeon/{mutant.file}, found it {found} times. "
            "Did someone change the dungeon? (Instructors: update grader/levels.py.)"
        )
    return source.replace(mutant.find, mutant.replace)


@contextmanager
def summoned(mutant: Mutant) -> Iterator[Path]:
    """Yield a path to a src/ folder that contains the mutated dungeon."""
    with tempfile.TemporaryDirectory(prefix="pytest-quest-monster-") as tmp:
        src = Path(tmp) / "src"
        shutil.copytree(ROOT / "src", src, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        target = src / "dungeon" / mutant.file
        target.write_text(apply(mutant, target.read_text(encoding="utf-8")), encoding="utf-8")
        yield src


def selftest(mutant: Mutant) -> str | None:
    """Return a problem description, or None if the monster can be summoned and compiles."""
    try:
        with summoned(mutant) as src:
            py_compile.compile(str(src / "dungeon" / mutant.file), doraise=True)
    except (MutantError, py_compile.PyCompileError) as exc:
        return str(exc)
    return None
