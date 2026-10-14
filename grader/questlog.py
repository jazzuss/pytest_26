"""The quest log: every commit that changes your tests explains what you did and why.

A quest log entry is a commit message like this (see .gitmessage):

    level-03: catch the shapeshifter with pytest.raises

    What: I added tests that check which exception type the backpack raises.
    Why: ValueError and InventoryFullError are different, and only an exact
         pytest.raises(InventoryFullError) notices when they get swapped.
    Learned: match= takes a regular expression, not plain text.

Rules: the first line starts with a tag (level-00 ... level-09, or boss), and
What: and Why: each have at least MIN_WORDS words. Learned: is optional.
Each entry must be your own words, so an entry copied from an earlier commit doesn't count.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from grader import ROOT

MIN_WORDS = 5
MIN_SUMMARY_WORDS = 3
LAST_LEVEL = 9

_SUBJECT = re.compile(r"^(?:level-?(?P<level>\d{1,2})|(?P<boss>boss))\s*:\s*(?P<summary>.*)$", re.IGNORECASE)
_FIELD = re.compile(r"^(?P<name>what|why|learned)\s*:\s*(?P<text>.*)$", re.IGNORECASE)
_TRAILER = re.compile(r"^[A-Za-z][A-Za-z-]*:\s")  # Co-authored-by: ..., Signed-off-by: ...
_SCISSORS = re.compile(r"^# -+ >8 -+$")
_WORD = re.compile(r"[^\W_]+(?:'[^\W_]+)?")

FIX_HINT = (
    "Fix the latest commit with `git commit --amend`, or an older one with "
    "`git rebase -i` (choose 'reword'). Then `git push --force-with-lease`."
)


def git_root() -> Path:
    """Whose history to read. The instructor's collector points this at a student's clone."""
    return Path(os.environ.get("GRADER_GIT_ROOT", ROOT))


def _words(text: str) -> int:
    return len(_WORD.findall(text))


@dataclass
class Entry:
    subject: str
    tag: str | None
    what: str
    why: str
    learned: str
    problems: list[str] = field(default_factory=list)
    sha: str = ""
    author: str = ""
    date: str = ""
    files: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    @property
    def short(self) -> str:
        return self.sha[:7]


def clean(message: str) -> str:
    """Drop comment lines (and everything below a `git commit -v` scissors line)."""
    kept = []
    for line in message.replace("\r\n", "\n").split("\n"):
        if _SCISSORS.match(line):
            break
        if line.startswith("#"):
            continue
        kept.append(line.rstrip())
    return "\n".join(kept).strip()


def parse(message: str) -> Entry:
    lines = clean(message).split("\n")
    subject = lines[0].strip() if lines else ""
    fields: dict[str, list[str]] = {"what": [], "why": [], "learned": []}
    current: str | None = None
    for raw in lines[1:]:
        line = raw.strip()
        match = _FIELD.match(line)
        if match:
            current = match["name"].lower()
            fields[current].append(match["text"].strip())
        elif _TRAILER.match(line):
            current = None
        elif current and line:
            fields[current].append(line)
    entry = Entry(
        subject=subject,
        tag=None,
        what=" ".join(fields["what"]).strip(),
        why=" ".join(fields["why"]).strip(),
        learned=" ".join(fields["learned"]).strip(),
    )
    _validate(entry)
    return entry


def _validate(entry: Entry) -> None:
    match = _SUBJECT.match(entry.subject)
    if not entry.subject:
        entry.problems.append("the first line is empty")
    elif not match:
        entry.problems.append(
            "the first line must start with a level tag, like 'level-03: catch the shapeshifter'"
        )
    else:
        if match["boss"]:
            entry.tag = "boss"
        elif int(match["level"]) > LAST_LEVEL:
            entry.problems.append(f"there is no level {match['level']}")
        else:
            entry.tag = f"level-{int(match['level']):02d}"
        summary_words = _words(match["summary"])
        if summary_words < MIN_SUMMARY_WORDS:
            entry.problems.append(
                f"the summary after '{entry.subject.split(':')[0]}:' needs at least "
                f"{MIN_SUMMARY_WORDS} words (has {summary_words})"
            )
    for name in ("what", "why"):
        count = _words(getattr(entry, name))
        if count < MIN_WORDS:
            entry.problems.append(
                f"'{name.title()}:' needs at least {MIN_WORDS} words in your own words (has {count})"
            )


# ---------------------------------------------------------------- git history


def _git(*args: str) -> str | None:
    try:
        done = subprocess.run(
            ["git", "-C", str(git_root()), "-c", "core.quotepath=off", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return None
    return done.stdout if done.returncode == 0 else None


def available() -> bool:
    return _git("rev-parse", "--is-inside-work-tree") is not None and _git("rev-parse", "HEAD") is not None


@lru_cache(maxsize=1)
def entries() -> tuple[Entry, ...] | None:
    """Quest log entries for every commit that changed tests/, oldest first.

    Skips the repository's first commit (the template itself) and merge commits.
    Returns None if there is no git history to read.
    """
    if not available():
        return None
    out = _git("log", "--reverse", "--date=short", "--name-only",
               "--format=%x1e%H%x1f%P%x1f%an%x1f%ad%x1f%B%x1f", "--", "tests")
    if out is None:
        return None
    found: list[Entry] = []
    seen: dict[tuple[str, str], str] = {}
    for record in out.split("\x1e"):
        if not record.strip():
            continue
        sha, parents, author, date, body, files = record.split("\x1f", 5)
        if len(parents.split()) != 1:
            continue
        entry = parse(body)
        entry.sha, entry.author, entry.date = sha, author, date
        entry.files = [line.strip() for line in files.splitlines() if line.strip()]
        key = (entry.what.lower(), entry.why.lower())
        if entry.what and entry.why:
            if key in seen:
                entry.problems.append(f"it is a copy of the entry in commit {seen[key]}")
            else:
                seen[key] = entry.short
        found.append(entry)
    return tuple(found)


def for_folder(folder: str) -> list[Entry] | None:
    all_entries = entries()
    if all_entries is None:
        return None
    prefix = folder.rstrip("/") + "/"
    return [e for e in all_entries if any(f.startswith(prefix) for f in e.files)]


def uncommitted(folder: str) -> bool:
    out = _git("status", "--porcelain", "--", folder)
    return bool(out and out.strip())


def staged_files() -> list[str]:
    out = _git("diff", "--cached", "--name-only")
    return [line for line in (out or "").splitlines() if line.strip()]


def merging() -> bool:
    return _git("rev-parse", "-q", "--verify", "MERGE_HEAD") is not None


def describe_problems(entry: Entry) -> str:
    return f"commit {entry.short} \"{entry.subject or '(empty)'}\": " + "; ".join(entry.problems)
