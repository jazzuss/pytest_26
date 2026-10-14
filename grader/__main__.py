"""PyTest Quest grader.

  python -m grader                 your scoreboard (checks every level)
  python -m grader check 3         check one level, with all the details
  python -m grader boss            fight the final boss
  python -m grader journal         read your quest log (your commit entries)
  python -m grader setup           install the commit template and hook (level 00)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

from grader import ROOT, questlog, report, seal
from grader.levels import BOSS_XP, LEVELS, MAX_XP, by_number, rank


def cmd_status(as_json: bool) -> int:
    from grader.engine import check_level

    results = []
    show_progress = not as_json and sys.stdout.isatty()
    for level in LEVELS:
        if show_progress:
            print(report.dim(f"  checking {level.label}...").ljust(70), end="\r", flush=True)
        results.append(check_level(level))
    if as_json:
        entries = questlog.entries()
        xp = sum(r.xp for r in results)
        print(json.dumps({
            "xp": xp,
            "max_xp": MAX_XP,
            "rank": rank(xp)[0],
            "levels": [{
                "number": r.level.number,
                "title": r.level.title,
                "cleared": r.cleared,
                "xp": r.xp,
                "monsters": r.monsters,
                "slain": r.slain,
                "problems": [c.title for c in r.failures],
            } for r in results],
            "seal": seal.verify(root=questlog.git_root()),
            "quest_log": None if entries is None else [{
                "sha": e.sha, "date": e.date, "author": e.author, "tag": e.tag,
                "subject": e.subject, "what": e.what, "why": e.why, "learned": e.learned,
                "ok": e.ok, "problems": e.problems,
            } for e in entries],
        }, indent=2))
        return 0
    if show_progress:
        print(" " * 70, end="\r")
    report.print_scoreboard(results)
    for r in results:
        if not r.cleared:
            print(f"  Next up: {report.bold(r.level.label)}. "
                  f"See the details with:  python -m grader check {r.level.number}")
            print(f"  Your mission is in {r.level.folder}/README.md\n")
            break
    return 0 if all(r.cleared for r in results) else 1


def cmd_check(which: str) -> int:
    from grader.engine import check_level

    if which == "all":
        levels = list(LEVELS)
    else:
        try:
            levels = [by_number(int(which))]
        except (ValueError, KeyError):
            print(f"There is no level {which!r}. Levels are 0-{LEVELS[-1].number}, or 'all'.")
            return 2
    ok = True
    for level in levels:
        print(report.dim(f"Checking {level.label}... (the monsters take a few seconds)"))
        result = check_level(level)
        report.print_level(result)
        report.summarize_level(result)
        ok = ok and result.cleared
    return 0 if ok else 1


def cmd_boss() -> int:
    from grader import boss

    print(report.bold("The Hydra stirs... first it checks every level."))
    levels, phases = boss.fight(on_level=lambda r: print(
        f"   {report.green('✔') if r.cleared else report.red('✘')} {r.level.label}"))
    won = boss.defeated(phases)
    report.print_boss(phases, won)
    report.print_scoreboard(levels, boss_defeated=won)
    report.summarize_boss(levels, phases, won)
    return 0 if won else 1


def cmd_journal(markdown: str | None) -> int:
    entries = questlog.entries()
    if entries is None:
        print("There is no git history here, so there is no quest log to read.")
        return 1
    if markdown:
        Path(markdown).write_text("# Quest log\n\n" + report.md_journal(list(entries)) + "\n", encoding="utf-8")
        print(f"Wrote {markdown}")
    else:
        report.print_journal(list(entries))
    return 0 if all(e.ok for e in entries) else 1


def cmd_setup() -> int:
    if not questlog.available():
        print("This folder isn't a git repository with commits yet. Clone your repo first.")
        return 1
    hook = ROOT / ".githooks" / "commit-msg"
    subprocess.run(["git", "-C", str(ROOT), "config", "commit.template", ".gitmessage"], check=True)
    subprocess.run(["git", "-C", str(ROOT), "config", "core.hooksPath", ".githooks"], check=True)
    if os.name != "nt" and hook.exists():
        hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(report.green("✔ Quest log template installed: `git commit` now opens it."))
    print(report.green("✔ Commit hook installed: commits to tests/ without a proper entry are stopped."))
    print()
    print("Tip: choose the editor git opens, for example VS Code:")
    print('     git config --global core.editor "code --wait"')
    return 0


def cmd_commit_msg(message_file: str) -> int:
    """Used by .githooks/commit-msg. Only commits that touch tests/ need an entry."""
    if questlog.merging():
        return 0
    message = Path(message_file).read_text(encoding="utf-8", errors="replace")
    touches_tests = any(f.startswith("tests/") for f in questlog.staged_files())
    entry = questlog.parse(message)
    looks_like_entry = entry.subject.lower().startswith(("level", "boss"))
    if not (touches_tests or looks_like_entry) or entry.ok:
        return 0
    print(report.red(report.bold("✘ This commit needs a quest log entry:")))
    for problem in entry.problems:
        print(report.red(f"   - {problem}"))
    print()
    print("  Write it like this:\n")
    print(report.dim("    level-03: catch the shapeshifter with pytest.raises\n"))
    print(report.dim("    What: I added a test that checks which exception the full backpack raises."))
    print(report.dim("    Why: InventoryFullError and ValueError are different types, and only"))
    print(report.dim("         an exact pytest.raises notices when they are swapped."))
    print()
    print("  Your message was saved in .git/COMMIT_EDITMSG. Run `git commit` again to retry.")
    return 1


def cmd_badges() -> int:
    """Swap the README's relative badge links for absolute ones (a fallback)."""
    remote = subprocess.run(["git", "-C", str(ROOT), "remote", "get-url", "origin"],
                            capture_output=True, text=True).stdout.strip()
    match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", remote)
    if not match:
        print(f"Couldn't find a GitHub repository in the 'origin' remote ({remote or 'none'}).")
        return 1
    base = f"https://github.com/{match[1]}/{match[2]}/actions/"
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    readme.write_text(text.replace("](../../actions/", f"]({base}").replace(
        "(../../actions/", f"({base}"), encoding="utf-8")
    print(f"Badge links now point to {base}. Commit and push README.md.")
    return 0


def cmd_seal() -> int:
    count = seal.write()
    print(f"Sealed {count} files in src/, grader/ and .github/ into grader/seal.json.")
    return 0


def cmd_selftest() -> int:
    from grader.mutants import selftest

    problems = seal.verify()
    for problem in problems:
        print(report.red(f"✘ seal: {problem}"))
    for level in LEVELS:
        for mutant in level.mutants:
            issue = selftest(mutant)
            mark = report.red("✘") if issue else report.green("✔")
            print(f"{mark} {level.tag} {mutant.name}" + (f": {issue}" if issue else ""))
            problems += [issue] if issue else []
    print(report.green("All monsters can be summoned.") if not problems else report.red("Problems found."))
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    report.setup_console()
    parser = argparse.ArgumentParser(prog="python -m grader", description="The PyTest Quest grader.")
    sub = parser.add_subparsers(dest="command")
    status = sub.add_parser("status", help="your scoreboard (the default)")
    status.add_argument("--json", action="store_true", help="machine-readable output (for instructors)")
    check = sub.add_parser("check", help="check one level in detail")
    check.add_argument("level", help="level number, or 'all'")
    sub.add_parser("boss", help="fight the final boss")
    journal = sub.add_parser("journal", help="read the quest log")
    journal.add_argument("--markdown", metavar="FILE", help="write it as a Markdown file instead")
    sub.add_parser("setup", help="install the commit template and commit hook")
    sub.add_parser("badges", help="use absolute badge links in README.md (if they show broken)")
    msg = sub.add_parser("commit-msg", help=argparse.SUPPRESS)
    msg.add_argument("file")
    sub.add_parser("seal", help="(instructors) re-seal src/, grader/ and .github/")
    sub.add_parser("selftest", help="(instructors) check that every monster can be summoned")
    args = parser.parse_args(argv)

    if args.command in (None, "status"):
        return cmd_status(getattr(args, "json", False))
    if args.command == "check":
        return cmd_check(args.level)
    if args.command == "boss":
        return cmd_boss()
    if args.command == "journal":
        return cmd_journal(args.markdown)
    if args.command == "setup":
        return cmd_setup()
    if args.command == "badges":
        return cmd_badges()
    if args.command == "commit-msg":
        return cmd_commit_msg(args.file)
    if args.command == "seal":
        return cmd_seal()
    if args.command == "selftest":
        return cmd_selftest()
    parser.print_help()
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:  # e.g. `python -m grader journal | head`
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(130)
