"""Everything the grader prints: terminal output, CI annotations, CI job summaries."""

from __future__ import annotations

import os
import sys
import textwrap

from grader import questlog
from grader.levels import BOSS_XP, LEVELS, MAX_XP, rank
from grader.model import Check, LevelResult

IN_CI = os.environ.get("GITHUB_ACTIONS") == "true"


# ------------------------------------------------------------------ console


def setup_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
    if os.name == "nt":
        os.system("")  # switches on ANSI colours in older Windows terminals


def _use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return IN_CI or bool(os.environ.get("FORCE_COLOR")) or sys.stdout.isatty()


def _paint(code: str):
    return lambda text: f"\033[{code}m{text}\033[0m" if _use_color() else text


green, red, yellow, cyan, bold, dim = (_paint(c) for c in ("32", "31", "33", "36", "1", "2"))


def _mark(check: Check) -> str:
    if check.skipped:
        return yellow("⏭")
    return green("✔") if check.ok else red("✘")


def _indent(text: str, prefix: str = "      ") -> str:
    return textwrap.indent(text, prefix)


def print_level(result: LevelResult) -> None:
    level = result.level
    print()
    print(bold(f"⚔  {level.label}") + dim(f"   ({level.skill})"))
    for check in result.checks:
        print(f"   {_mark(check)} {check.title}")
        if check.detail and (not check.ok or check.skipped):
            print(dim(_indent(check.detail)))
    print()
    if result.cleared:
        print(green(bold(f"   LEVEL CLEARED  +{level.xp} XP")))
    else:
        left = len(result.failures)
        print(red(bold(f"   Not cleared yet: {left} thing{'s' if left != 1 else ''} left to do.")))
    print()


def print_scoreboard(results: list[LevelResult], boss_defeated: bool | None = None) -> None:
    xp = sum(r.xp for r in results) + (BOSS_XP if boss_defeated else 0)
    print()
    print(bold("  PYTEST QUEST · SCOREBOARD"))
    print("  " + "─" * 58)
    for r in results:
        if r.cleared:
            print(f"  {green('✔')} {r.level.number:02d}  {r.level.title:<24} {green(f'{r.level.xp:>4} XP')}")
        else:
            first = r.failures[0].title if r.failures else ""
            print(f"  {red('✘')} {r.level.number:02d}  {r.level.title:<24} {dim(f'0/{r.level.xp:<4}')} "
                  f"{dim(first[:40])}")
    if boss_defeated is None:
        print(f"  {yellow('🐉')} {'Final Boss':<28} {dim('fight it with: python -m grader boss')}")
    elif boss_defeated:
        print(f"  {green('✔')} {'Final Boss':<28} {green(f'{BOSS_XP:>4} XP')}")
    else:
        print(f"  {red('✘')} {'Final Boss':<28} {dim(f'0/{BOSS_XP}')}")
    print("  " + "─" * 58)
    filled = round(20 * xp / MAX_XP)
    current, upcoming = rank(xp)
    print(f"  XP {xp}/{MAX_XP}  [{green('█' * filled)}{dim('░' * (20 - filled))}]  "
          f"Rank: {bold(current)}")
    if upcoming:
        print(dim(f"  Next rank: {upcoming[1]} at {upcoming[0]} XP"))
    print()


def print_boss(phases: list[Check], won: bool) -> None:
    print()
    print(bold("🐉  THE FINAL BOSS: THE PYTEST HYDRA"))
    for phase in phases:
        print(f"   {_mark(phase)} {phase.title}")
        if phase.detail and (not phase.ok or phase.skipped):
            print(dim(_indent(phase.detail)))
    print()
    if won:
        print(green(bold("   THE HYDRA IS DEFEATED. You are a Legend of Pytest. 🏆")))
    else:
        print(red(bold("   The Hydra still stands.")))
    print()


def print_journal(entries: list[questlog.Entry]) -> None:
    if not entries:
        print("No quest log entries yet.")
        return
    for tag, group in _grouped(entries):
        print(bold(f"\n{tag}"))
        for e in group:
            status = green("✔") if e.ok else red("✘")
            print(f"  {status} {e.date} {e.short} {e.author}: {e.subject}")
            for name in ("what", "why", "learned"):
                text = getattr(e, name)
                if text:
                    print(_indent(textwrap.fill(f"{name.title()}: {text}", 90), "      "))
            if e.problems:
                print(red(_indent("Problem: " + "; ".join(e.problems), "      ")))
    print()


def _grouped(entries: list[questlog.Entry]) -> list[tuple[str, list[questlog.Entry]]]:
    order = [level.tag for level in LEVELS] + ["boss"]
    groups: dict[str, list[questlog.Entry]] = {}
    for e in entries:
        groups.setdefault(e.tag or "untagged", []).append(e)
    return [(tag, groups[tag]) for tag in order + ["untagged"] if tag in groups]


# ------------------------------------------------------------------ GitHub Actions


def _escape(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def annotate(title: str, checks: list[Check]) -> None:
    """Show failures as annotations on the workflow run page."""
    if not IN_CI:
        return
    for check in checks:
        if not check.ok and not check.skipped:
            first_line = check.detail.splitlines()[0] if check.detail else ""
            print(f"::error title={_escape(title)}::{_escape(check.title + ': ' + first_line)}")


def _summary_write(markdown: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(markdown + "\n")


def _md_checks(checks: list[Check]) -> str:
    rows = ["| | Check |", "|---|---|"]
    details = []
    for c in checks:
        icon = "⏭️" if c.skipped else ("✅" if c.ok else "❌")
        rows.append(f"| {icon} | {c.title} |")
        if c.detail and (not c.ok or c.skipped):
            details.append(f"<details><summary>{c.title}</summary>\n\n```\n{c.detail}\n```\n</details>")
    return "\n".join(rows) + ("\n\n" + "\n".join(details) if details else "")


def md_journal(entries: list[questlog.Entry]) -> str:
    if not entries:
        return "_No quest log entries yet._"
    out = []
    for tag, group in _grouped(entries):
        out.append(f"#### {tag}")
        for e in group:
            icon = "✅" if e.ok else "❌"
            out.append(f"- {icon} **{e.subject}** · `{e.short}` · {e.date} · {e.author}")
            for name in ("what", "why", "learned"):
                text = getattr(e, name)
                if text:
                    out.append(f"  - **{name.title()}:** {text}")
            if e.problems:
                out.append(f"  - ⚠️ {'; '.join(e.problems)}")
    return "\n".join(out)


def summarize_level(result: LevelResult) -> None:
    annotate(result.level.label, result.checks)
    verdict = f"CLEARED · +{result.level.xp} XP 🟢" if result.cleared else "not cleared yet 🔴"
    md = [f"## ⚔️ {result.level.label}: {verdict}",
          f"_Skill: {result.level.skill}_", "", _md_checks(result.checks)]
    mine = questlog.for_folder(result.level.folder)
    if mine:
        md += ["", "### 📜 Quest log for this level", md_journal(mine)]
    _summary_write("\n".join(md))


def summarize_boss(levels: list[LevelResult], phases: list[Check], won: bool) -> None:
    annotate("Final Boss", phases)
    xp = sum(r.xp for r in levels) + (BOSS_XP if won else 0)
    current, _ = rank(xp)
    md = [f"## 🐉 The Pytest Hydra: {'DEFEATED 🏆' if won else 'still standing'}",
          f"**XP {xp}/{MAX_XP} · Rank: {current}**", "", "### Phases", _md_checks(phases),
          "", "### Levels", "| | Level | XP |", "|---|---|---|"]
    for r in levels:
        md.append(f"| {'✅' if r.cleared else '❌'} | {r.level.label} | {r.xp}/{r.level.xp} |")
    entries = questlog.entries()
    if entries is not None:
        md += ["", "### 📜 Quest log", md_journal(list(entries))]
    _summary_write("\n".join(md))
