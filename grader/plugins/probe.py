"""Records what pytest collected and how every test ended, as JSON.

Loaded by the grader with `-p grader.plugins.probe`. Writes to the file named
in the GRADER_PROBE_OUT environment variable.
"""

from __future__ import annotations

import json
import os
from typing import Any

_items: list[dict[str, Any]] = []
_results: dict[str, dict[str, Any]] = {}
_state = {"deselected": 0, "collect_errors": 0}


def _plain(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


def _describe(item: Any) -> dict[str, Any]:
    callspec = getattr(item, "callspec", None)
    return {
        "nodeid": item.nodeid,
        "test": item.nodeid.split("[", 1)[0],
        "path": str(item.path),
        "fixtures": list(getattr(item, "fixturenames", [])),
        "parametrized": callspec is not None,
        "markers": [
            {
                "name": mark.name,
                "args": [_plain(a) for a in mark.args],
                "kwargs": {k: _plain(v) for k, v in mark.kwargs.items()},
            }
            for mark in item.iter_markers()
        ],
    }


def pytest_collection_finish(session: Any) -> None:
    _items.extend(_describe(item) for item in session.items)


def pytest_deselected(items: list[Any]) -> None:
    _state["deselected"] += len(items)


def pytest_collectreport(report: Any) -> None:
    if report.failed:
        _state["collect_errors"] += 1


def pytest_runtest_logreport(report: Any) -> None:
    result = _results.setdefault(report.nodeid, {"outcome": "passed", "duration": 0.0})
    result["duration"] += report.duration
    if report.failed:
        result["outcome"] = "failed" if report.when == "call" else "error"
    elif report.skipped:
        if hasattr(report, "wasxfail"):
            result["outcome"] = "xfailed"
        elif result["outcome"] == "passed":
            result["outcome"] = "skipped"
    elif report.when == "call" and hasattr(report, "wasxfail"):
        result["outcome"] = "xpassed"


def pytest_sessionfinish(session: Any) -> None:
    out = os.environ.get("GRADER_PROBE_OUT")
    if not out:
        return
    data = {
        "items": _items,
        "results": _results,
        "deselected": _state["deselected"],
        "collect_errors": _state["collect_errors"],
        "markers": list(session.config.getini("markers")),
    }
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
