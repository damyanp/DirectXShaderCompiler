#!/usr/bin/env python3
"""Reject leaked checkout or user-profile paths in committable triage text."""

from collections import defaultdict
from pathlib import Path
import re
import sys


SKILL_DIR = Path(__file__).resolve().parent.parent
EXCLUDED_DIRS = {".cache", "bin", "out", "__pycache__"}

# Match both ordinary text and JSON's doubled separators. These are the two
# machine-owned roots this workflow has leaked in practice; system paths and
# paths embedded in compiler output are evidence, not contributor layouts.
MACHINE_PATH = re.compile(
    rb"(?i)[A-Z]:\\{1,2}(?:prj|Users)\\{1,2}"
)

# Exact counts make this an allowlist rather than a blanket exemption: a new
# path in one of these files changes the count and fails the gate.
ALLOWLIST = {
    # The method intentionally quotes the patterns the gate must detect.
    "SKILL.md": (3, "documents raw and JSON-escaped path-leak patterns"),
    # The orchestrator notes preserve the failed scans and their controls.
    "data/reports/batch-009-orchestrator-notes.md": (
        6, "records the path-redaction incident; rewriting it destroys the lesson"
    ),
    # The issue-local lesson demonstrates why one separator spelling misses the other.
    "data/issues/3237/method-notes.md": (
        4, "documents the raw-versus-JSON escaping trap"
    ),
    # These are the reporter's already-public paths, quoted verbatim by fetch.
    "data/issues/3429/issue.json": (
        3, "preserves paths from the public issue rather than rewriting evidence"
    ),
}


def validate_matcher():
    """Prove the regex sees both separator forms and rejects unrelated paths."""
    slash = b"\\"
    positives = (
        b"C:" + slash + b"prj" + slash + b"repo",
        b"C:" + slash * 2 + b"Users" + slash * 2 + b"name",
    )
    negatives = (
        b"<repo>/build/bin/dxc.exe",
        b"C:" + slash + b"Program Files" + slash + b"tool.exe",
        b"relative" + slash + b"Users" + slash + b"name",
    )
    if not all(MACHINE_PATH.search(value) for value in positives):
        raise RuntimeError("machine-path regex missed a positive control")
    if any(MACHINE_PATH.search(value) for value in negatives):
        raise RuntimeError("machine-path regex matched a negative control")


def committable_text_files():
    """Yield text files, excluding local/generated directory classes by path."""
    for path in sorted(SKILL_DIR.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(SKILL_DIR)
        if any(part.lower() in EXCLUDED_DIRS for part in relative.parts):
            continue
        data = path.read_bytes()
        if b"\0" in data:
            continue
        yield relative.as_posix(), data


def find_hits(data):
    for match in MACHINE_PATH.finditer(data):
        line = data.count(b"\n", 0, match.start()) + 1
        line_start = data.rfind(b"\n", 0, match.start()) + 1
        column = match.start() - line_start + 1
        yield line, column, match.group().decode("ascii")


def main():
    validate_matcher()
    hits = defaultdict(list)
    file_count = 0
    for relative, data in committable_text_files():
        file_count += 1
        hits[relative].extend(find_hits(data))

    failures = []
    for relative, matches in sorted(hits.items()):
        if relative not in ALLOWLIST:
            for line, column, value in matches:
                failures.append(
                    f"{relative}:{line}:{column}: unexpected machine path {value!r}"
                )

    for relative, (expected, reason) in ALLOWLIST.items():
        actual = len(hits.get(relative, ()))
        if actual != expected:
            failures.append(
                f"{relative}: allowlist expected {expected} match(es), found "
                f"{actual} ({reason})"
            )

    if failures:
        print("machine-path gate failed:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1

    allowed_count = sum(expected for expected, _ in ALLOWLIST.values())
    print(
        f"path check passed: {file_count} committable text files; "
        f"{allowed_count} allowlisted matches in {len(ALLOWLIST)} files; "
        "no unexpected machine paths"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
