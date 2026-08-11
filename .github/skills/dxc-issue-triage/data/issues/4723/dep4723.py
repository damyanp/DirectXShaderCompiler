"""#4723 harness: run dxc, then report which files the run actually produced.

The reported gap is about **flag handling and file output** -- whether the
``-M`` / ``-MD`` / ``-MF`` depfile flags do anything when ``-P`` is also on the
command line.  The observable is therefore the *set of artifacts a run wrote*,
not stdout and not DXIL, and a bare ``dxc`` invocation cannot put that into a
scored capture: the depfile either appears next to the shader or it does not,
and ``triage.py run`` only ever sees stdout/stderr.

So this is registered as a compiler (SKILL.md: "When the symptom is in a pass
dxc.exe cannot run, register the harness as a compiler"), which keeps ``run``,
``--shader``, ``--args``, ``--expect``, ``audit`` and ``reindex`` all working.

Three properties that the evidence depends on:

* **Exit status comes from Python.**  ``%ERRORLEVEL%`` inside a single ``cmd``
  line is expanded at parse time, so a ``.cmd`` harness cheerfully prints
  ``EXIT=0`` for a run that failed.  Measured here while exploring: every
  ``cmd /c "dxc ... & echo EXIT=%ERRORLEVEL%"`` probe reported 0 regardless.
  ``subprocess`` returns the real status and it is printed as a full 32-bit
  HRESULT, because DXC returns E_FAIL (0x80004005) for ordinary diagnosed
  errors and those must not be read as crashes.

* **Every expected artifact is deleted before the run.**  A stale ``.d`` left
  by an earlier probe would otherwise read exactly like a depfile this run
  wrote.  The mirror of that trap -- a *missing* directory faking the bug --
  is handled by creating any directory an expected artifact needs.

* **Absence is reported positively.**  A missing depfile is printed as
  ``dep4723-artifact ... MISSING``, a line that only exists because the harness
  ran, parsed the command line and looked.  A predicate anchored on that cannot
  be satisfied for free by a run that never started, which a bare
  ``not_contains`` clause would be.

One knob, so the same harness can date the behaviour across releases:

    DXC_EXE   the dxc.exe under test; defaults to this repo's Debug build.

No absolute path is baked in -- the default is derived from this file's own
location -- so the repro runs from a fresh clone.

The harness's own exit code is deliberately a small integer -- 0 all clean,
1 something exited with a diagnosed error, 3 something exited with a status
that means the compiler fell over -- and never the raw HRESULT. cmd.exe cannot
carry a value like 0x80004005 out of a batch file intact (it arrived as
0xFFFFFFFF, which reads like a crash and is not one), so the real status is
reported in the text as ``dep4723-exit=0x........`` and classified on the
``dep4723-status=`` line, where nothing can mangle it.
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# <repo>/.github/skills/dxc-issue-triage/data/issues/4723 -> <repo>
REPO = os.path.abspath(os.path.join(HERE, *([os.pardir] * 6)))
SKILL_SCRIPTS = os.path.join(REPO, ".github", "skills", "dxc-issue-triage",
                             "scripts")
DEFAULT_DXC = os.path.join(REPO, "build", "Debug", "bin", "dxc.exe")

sys.path.insert(0, SKILL_SCRIPTS)
import triage  # noqa: E402  -- committed beside this file; see redact() below


def redact(text):
    """Strip this machine's layout from anything that gets captured.

    Delegated to ``triage.redact_paths`` rather than reimplemented, so the
    harness and the tool tokenise identically and ``check_paths.py`` has one
    definition to check against.
    """
    return triage.redact_paths(text)


def show(path):
    return triage.display_exe(path)


# A make rule, i.e. `<target>: <prerequisite> ...`. The negative lookahead
# matters: a clang diagnostic (`repro.hlsl:5:3: error: ...`) has the same
# shape, so without it a build that merely failed loudly would satisfy the
# `-M` self-test and the predicate could manufacture a clean instrument out of
# an error message. The caller additionally requires the source's own name on
# the line, which no unrelated output carries.
DEP_LINE = re.compile(r"^(?!.*\b(?:error|warning|fatal|note)\b)\S+:\s+\S+",
                      re.MULTILINE)


def stdout_dep_lines(text, source):
    """Dependency-list lines `-M` printed to the console, if any."""
    name = os.path.basename(source) if source else ""
    return [ln for ln in text.splitlines()
            if DEP_LINE.match(ln) and name and name in ln]


def snapshot(root):
    """Relative path -> size, for every file under `root`."""
    seen = {}
    for base, _dirs, files in os.walk(root):
        for name in files:
            full = os.path.join(base, name)
            try:
                seen[os.path.relpath(full, root)] = os.path.getsize(full)
            except OSError:
                pass
    return seen


def value_of(args, i, flag):
    """Value of a JoinedOrSeparate option at args[i], or None."""
    tok = args[i]
    body = tok[1:]
    if body[:len(flag)].upper() != flag:
        return None
    rest = body[len(flag):]
    if rest:
        return rest.lstrip(":=")
    return args[i + 1] if i + 1 < len(args) else None


def expected_artifacts(args):
    """Artifacts this command line asks dxc to produce.

    Returned as (kind, path) pairs. `stdout-deps` is a pseudo-artifact: `-M`
    writes the dependency list to the console rather than to a file.
    """
    want, preprocess, source, fi = [], False, None, None
    i = 0
    while i < len(args):
        tok = args[i]
        if tok[:1] in "-/" and len(tok) > 1:
            up = tok[1:].upper()
            if up in ("P", "PO"):
                preprocess = True
            elif up == "M":
                want.append(("stdout-deps", "<stdout>"))
            elif up == "MD":
                want.append(("depfile-MD", None))          # resolved below
            elif up[:2] == "MF":
                v = value_of(args, i, "MF")
                if v:
                    want.append(("depfile-MF", v))
                    if not tok[1:].upper()[2:]:
                        i += 1
            elif up[:2] == "FI":
                fi = value_of(args, i, "FI")
                if fi and not tok[1:].upper()[2:]:
                    i += 1
            elif up[:2] == "FO":
                v = value_of(args, i, "FO")
                if v:
                    want.append(("object-Fo", v))
                    if not tok[1:].upper()[2:]:
                        i += 1
        elif tok.lower().endswith((".hlsl", ".hlsli")):
            source = tok
        i += 1

    stem = os.path.splitext(source)[0] if source else "a"
    resolved = []
    for kind, path in want:
        resolved.append((kind, stem + ".d" if kind == "depfile-MD" else path))
    if preprocess:
        resolved.append(("preprocessed-P", fi or stem + ".i"))
    elif fi:
        resolved.append(("preprocessed-Fi", fi))
    return resolved, source


def clear(path):
    """Remove a stale artifact and make sure its directory exists.

    Both halves matter. A leftover `.d` from an earlier probe reads exactly
    like one this run produced; and a directory git could not store (git does
    not track empty directories) makes a re-run fail with "cannot find the
    path specified", which looks precisely like the bug under test.
    """
    if path in (None, "<stdout>"):
        return
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
        print(f"dep4723-created-dir {redact(parent)}")
    if os.path.isfile(path):
        os.remove(path)
        print(f"dep4723-cleared {redact(path)}")


def lines_of(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return [ln.rstrip("\n") for ln in f]
    except OSError:
        return []


def head_of(path, limit=8):
    return lines_of(path)[:limit]


def tail_of(path, limit=3):
    """Last few non-empty lines of an artifact.

    The head of a preprocessed file is always `#line 1 "..."` and tells you
    nothing; what a depfile flag does to it shows up only at the end. Reporting
    the tail is what turned this issue from "the flags do nothing" into "the
    dependency list is written into the preprocessed output".
    """
    body = [ln for ln in lines_of(path) if ln.strip()]
    return body[-limit:]


def run(argv):
    print("$ dxc " + subprocess.list2cmdline(argv[1:]))
    sys.stdout.flush()
    p = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    text = redact((p.stdout or "") + (p.stderr or ""))
    if text.strip():
        print("--- dxc output ---")
        print(text if text.endswith("\n") else text + "\n", end="")
        print("--- end dxc output ---")
    else:
        print("--- dxc output: EMPTY ---")
    return p.returncode, text


def classify_status(rc):
    """('clean'|'diagnosed'|'internal', small exit code) for a dxc status."""
    status = rc & 0xFFFFFFFF
    if status == 0:
        return "clean", 0
    if status in triage.INTERNAL_STATUS:
        return "internal", 3
    return "diagnosed", 1


def main():
    dxc = os.environ.get("DXC_EXE") or DEFAULT_DXC
    args = sys.argv[1:]

    if not args or "--version" in args or "-version" in args:
        print("dep4723 harness (issue 4723): runs DXC_EXE, then reports which "
              "artifacts the run actually produced")
        print("dep4723-dxc=" + show(dxc))
        rc, _ = run([dxc, "--version"])
        return classify_status(rc)[1]

    print("dep4723-dxc=" + show(dxc))
    want, source = expected_artifacts(args)
    for _kind, path in want:
        clear(path)
    for _kind, path in want:
        print(f"dep4723-requested {_kind} {redact(path)}")

    before = snapshot(".")
    rc, text = run([dxc] + args)
    after = snapshot(".")

    print(f"dep4723-exit=0x{rc & 0xFFFFFFFF:08X}")
    kind, code = classify_status(rc)
    print(f"dep4723-status={kind}")

    for rel in sorted(set(after) - set(before)):
        print(f"dep4723-created {rel.replace(os.sep, '/')} bytes={after[rel]}")
    for rel in sorted(r for r in after if r in before
                      and after[r] != before[r]):
        print(f"dep4723-modified {rel.replace(os.sep, '/')} "
              f"bytes={after[rel]}")

    for kind, path in want:
        if path == "<stdout>":
            lines = stdout_dep_lines(text, source)
            print(f"dep4723-artifact {kind} <stdout> "
                  + ("PRESENT" if lines else "MISSING"))
            for line in lines[:8]:
                print(f"dep4723-content <stdout> | {redact(line)}")
            continue
        shown = redact(path).replace(os.sep, "/")
        if os.path.isfile(path):
            print(f"dep4723-artifact {kind} {shown} PRESENT "
                  f"bytes={os.path.getsize(path)}")
            for line in head_of(path):
                print(f"dep4723-content {shown} | {redact(line)}")
            for line in tail_of(path):
                print(f"dep4723-tail {shown} | {redact(line)}")
        else:
            print(f"dep4723-artifact {kind} {shown} MISSING")

    print(f"dep4723-selftest artifacts-inspected={len(want)}")
    return code


if __name__ == "__main__":
    sys.exit(main())
