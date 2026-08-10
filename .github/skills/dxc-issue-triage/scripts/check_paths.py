#!/usr/bin/env python3
"""Reject leaked checkout or user-profile paths in committable triage text.

Run from anywhere:

    python scripts/check_paths.py
    python scripts/check_paths.py --issue 3902
    python scripts/check_paths.py --path data/issues/3902
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path


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


def _within(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_scope(issue=None, path=None):
    if issue is not None and path is not None:
        raise ValueError("--issue and --path are mutually exclusive")
    if issue is not None:
        scope = SKILL_DIR / "data" / "issues" / str(issue)
    elif path is not None:
        scope = Path(path)
        if not scope.is_absolute():
            scope = SKILL_DIR / scope
    else:
        scope = SKILL_DIR
    scope = scope.resolve()
    if not _within(scope, SKILL_DIR.resolve()):
        raise ValueError(f"scope escapes the triage skill: {scope}")
    if not scope.exists():
        raise ValueError(f"scope does not exist: {scope}")
    return scope


def _utf16_view(data):
    """Decode UTF-16 text before the binary sniff sees its expected NULs."""
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        encoding = "utf-16"
    else:
        sample = data[:8192]
        pairs = len(sample) // 2
        if pairs < 4:
            return None
        even_nuls = sample[0:2 * pairs:2].count(0) / pairs
        odd_nuls = sample[1:2 * pairs:2].count(0) / pairs
        if odd_nuls >= 0.30 and even_nuls <= 0.05:
            encoding = "utf-16-le"
        elif even_nuls >= 0.30 and odd_nuls <= 0.05:
            encoding = "utf-16-be"
        else:
            return None
    try:
        return data.decode(encoding).encode("utf-8")
    except UnicodeDecodeError:
        return None


def _looks_binary(data):
    """Distinguish genuine binary data from text containing an isolated NUL."""
    sample = data[:8192]
    if not sample:
        return False
    controls = sum(
        byte < 32 and byte not in (9, 10, 12, 13) for byte in sample)
    return controls / len(sample) > 0.10


def text_view(data):
    if b"\0" not in data:
        return data
    decoded = _utf16_view(data)
    if decoded is not None:
        return decoded
    if _looks_binary(data):
        return None
    return data


def committable_text_files(scope):
    """Yield text files, excluding local/generated directory classes by path."""
    paths = [scope] if scope.is_file() else sorted(scope.rglob("*"))
    for file_path in paths:
        if not file_path.is_file():
            continue
        relative = file_path.relative_to(SKILL_DIR)
        if any(part.lower() in EXCLUDED_DIRS for part in relative.parts):
            continue
        data = text_view(file_path.read_bytes())
        if data is not None:
            yield relative.as_posix(), data


def find_hits(data):
    for match in MACHINE_PATH.finditer(data):
        line = data.count(b"\n", 0, match.start()) + 1
        line_start = data.rfind(b"\n", 0, match.start()) + 1
        column = match.start() - line_start + 1
        yield line, column, match.group().decode("ascii")


def scan(issue=None, path=None):
    """Return (failures, file_count, allowed_hits, allowlisted_files)."""
    validate_matcher()
    scope = resolve_scope(issue, path)
    hits = defaultdict(list)
    file_count = 0
    for relative, data in committable_text_files(scope):
        file_count += 1
        hits[relative].extend(find_hits(data))

    failures = []
    for relative, matches in sorted(hits.items()):
        if relative not in ALLOWLIST:
            for line, column, value in matches:
                failures.append(
                    f"{relative}:{line}:{column}: unexpected machine path "
                    f"{value!r}")

    relevant_allowlist = {
        relative: detail for relative, detail in ALLOWLIST.items()
        if _within((SKILL_DIR / relative).resolve(), scope)
    }
    for relative, (expected, reason) in relevant_allowlist.items():
        actual = len(hits.get(relative, ()))
        if actual != expected:
            failures.append(
                f"{relative}: allowlist expected {expected} match(es), found "
                f"{actual} ({reason})")

    return (failures, file_count,
            sum(len(hits.get(relative, ()))
                for relative in relevant_allowlist),
            len(relevant_allowlist))


def main(argv=None):
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--issue", type=int)
    group.add_argument("--path")
    args = parser.parse_args(argv)
    try:
        failures, file_count, allowed_count, allowlisted_files = scan(
            issue=args.issue, path=args.path)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    if failures:
        print("machine-path gate failed:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1

    print(
        f"path check passed: {file_count} committable text files; "
        f"{allowed_count} allowlisted matches in {allowlisted_files} files; "
        "no unexpected machine paths")
    return 0


if __name__ == "__main__":
    sys.exit(main())
