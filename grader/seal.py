"""The seal: fingerprints of the files students must not change.

Testers don't change the code to make their tests pass. The seal turns that
rule into a check. Instructors re-seal after editing with:  python -m grader seal
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from grader import ROOT

SEALED = ("src", "grader", ".github")
SEAL_FILE = ROOT / "grader" / "seal.json"
_IGNORED_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}


def _files(root: Path, dirs: tuple[str, ...]) -> list[Path]:
    files = []
    for name in dirs:
        base = root / name
        if not base.exists():
            continue
        for path in base.rglob("*"):
            rel = path.relative_to(root)
            if (
                path.is_file()
                and "__pycache__" not in rel.parts
                and path.suffix != ".pyc"
                and path.name not in _IGNORED_NAMES
                and rel.as_posix() != "grader/seal.json"
            ):
                files.append(path)
    return sorted(files)


def _digest(path: Path) -> str:
    # Line endings are normalised so a Windows checkout (CRLF) still matches.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def compute(root: Path = ROOT, dirs: tuple[str, ...] = SEALED) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): _digest(p) for p in _files(root, dirs)}


def write() -> int:
    seal = compute()
    SEAL_FILE.write_text(json.dumps(seal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return len(seal)


def verify(dirs: tuple[str, ...] = SEALED, root: Path = ROOT) -> list[str]:
    """Problems like 'modified: src/dungeon/hero.py'. Empty list = untouched."""
    if not SEAL_FILE.exists():
        return ["missing: grader/seal.json"]
    expected = {
        path: digest
        for path, digest in json.loads(SEAL_FILE.read_text(encoding="utf-8")).items()
        if path.split("/", 1)[0] in dirs
    }
    actual = compute(root, dirs)
    problems = []
    for path in sorted(expected.keys() | actual.keys()):
        if path not in actual:
            problems.append(f"missing: {path}")
        elif path not in expected:
            problems.append(f"added: {path}")
        elif expected[path] != actual[path]:
            problems.append(f"modified: {path}")
    return problems
