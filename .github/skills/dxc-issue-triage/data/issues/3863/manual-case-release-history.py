"""Issue 3863: has `-H` EVER printed anything during `-P`, in any release?

Why this is a hand-written matrix and not `triage.py bisect`:

`-P` changed grammar in the middle of the release range. Before 8bf2b087c
(PR #4624, 2022-08-31, first shipped in v1.7.2212) `-P` was `Separate`, so
`-P <name>` consumed the next token as the *output* file and `-Fi` did not
exist; afterwards `-P` is a `Flag` and `-Fi` names the output. No single
command line means the same thing on both sides of that commit, so a bisect
driven by one fixed command line would be measuring the grammar change, not the
symptom. This probes each release with the spelling that release accepts and
records which grammar answered.

The date this was filed (2021-07-07) falls inside the release range and both
endpoints agree, which SKILL.md flags as the signature of a possible mid-history
window -- so this is a LINEAR sweep of every stable release, not a bisect.

Per release, six measurements. Two exist to keep the interesting one honest:

  compile+-H       POSITIVE CONTROL. `-H` on a normal compile must print the
                   trace. If it does not, that release cannot answer the
                   question at all and its silence under -P proves nothing.
  preprocessed     Did the probe actually preprocess (output exists and carries
                   both header bodies)? A release that never ran is not a data
                   point.
  -P +-H           THE SYMPTOM.
  -P +-Vi          the documented alias, in case only one spelling was wired.
  compile+-M       when did the dependency-listing alternative become available?
  -P +-M           the adjacent open request to make -M work under -P.

Every release runs in its own scratch directory containing copies of the repro
and its headers, and the SHA-256 of each input is checked afterwards: on the old
grammar a misplaced token makes dxc treat the SOURCE as the OUTPUT and overwrite
it at exit 0, which is how this option surface destroyed evidence once before.
Mutation is reported loudly rather than worked around.

Usage (from the workspace root):
    python data/issues/3863/manual-case-release-history.py > \
           data/issues/3863/manual-case-release-history.txt
"""
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
import triage  # noqa: E402

SOURCES = ("repro.hlsl", "inc-pp-a.h", "inc-pp-b.h")
BODY_MARKERS = ("ppmarker3863 = 1;", "ppnested3863 = 2;")
TRACE = "Opening file ["
UNKNOWN = "Unknown argument"
TIMEOUT = 90


def run(exe, argv, cwd):
    try:
        p = subprocess.run([exe] + argv, cwd=cwd, capture_output=True,
                           timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return -1, "<timed out after %ds>" % TIMEOUT
    out = (p.stdout or b"") + (p.stderr or b"")
    return p.returncode, out.decode("utf-8", "replace")


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def preprocessed_ok(cwd, name):
    path = os.path.join(cwd, name)
    if not os.path.isfile(path):
        return False
    text = open(path, "rb").read().decode("utf-8", "replace")
    return all(m in text for m in BODY_MARKERS)


def probe(tag, exe):
    """One release. Returns a dict of measurements plus any integrity alarm."""
    work = os.path.join(HERE, "work-history", tag.replace("/", "_"))
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    for s in SOURCES:
        shutil.copy(os.path.join(HERE, s), work)
    before = {s: sha(os.path.join(work, s)) for s in SOURCES}

    r = {"tag": tag, "alarm": ""}

    ver_rc, ver = run(exe, ["--version"], work)
    r["version"] = " ".join(ver.split())[:70] if ver_rc == 0 else "?"

    # Which -P grammar does this release speak? Ask, do not assume.
    rc, out = run(exe, ["-P", "repro.hlsl", "-Fi", "g-new.i"], work)
    if rc == 0 and preprocessed_ok(work, "g-new.i"):
        r["grammar"] = "new"
        pp = lambda out_name, extra: (            # noqa: E731
            ["-P", "repro.hlsl", "-Fi", out_name] + extra)
    else:
        rc2, out2 = run(exe, ["-P", "g-old.i", "repro.hlsl"], work)
        if rc2 == 0 and preprocessed_ok(work, "g-old.i"):
            r["grammar"] = "old"
            pp = lambda out_name, extra: (        # noqa: E731
                ["-P", out_name, "repro.hlsl"] + extra)
        else:
            r["grammar"] = "??"
            r["note"] = ("neither grammar preprocessed: new->%s | old->%s"
                         % (" ".join(out.split())[:60],
                            " ".join(out2.split())[:60]))
            pp = lambda out_name, extra: (        # noqa: E731
                ["-P", "repro.hlsl", "-Fi", out_name] + extra)

    # POSITIVE CONTROL: -H on an ordinary compile.
    rc, out = run(exe, ["-T", "ps_6_0", "-E", "main", "-H", "repro.hlsl"], work)
    r["compile_H"] = TRACE in out
    r["compile_rc"] = rc

    # THE SYMPTOM, plus the alias.
    rc, out = run(exe, pp("h.i", ["-H"]), work)
    r["p_H"] = TRACE in out
    r["p_H_rc"] = rc
    r["p_H_rejected"] = UNKNOWN in out
    r["p_H_ran"] = preprocessed_ok(work, "h.i")
    r["p_H_say"] = " ".join(out.split())[:70]

    rc, out = run(exe, pp("vi.i", ["-Vi"]), work)
    r["p_Vi"] = TRACE in out
    r["p_Vi_rejected"] = UNKNOWN in out
    r["p_Vi_ran"] = preprocessed_ok(work, "vi.i")

    # The alternative the reporter would be told to use today, and the
    # adjacent open request to make it work under -P.
    rc, out = run(exe, ["-T", "ps_6_0", "-E", "main", "-M", "repro.hlsl"], work)
    r["compile_M"] = (rc == 0 and UNKNOWN not in out
                      and "inc-pp-a.h" in out)
    r["compile_M_rejected"] = UNKNOWN in out

    rc, out = run(exe, pp("m.i", ["-M"]), work)
    r["p_M"] = (UNKNOWN not in out and "inc-pp-a.h" in out)
    r["p_M_rejected"] = UNKNOWN in out

    after = {s: sha(os.path.join(work, s)) for s in SOURCES}
    for s in SOURCES:
        if before[s] != after[s]:
            r["alarm"] += " INPUT MUTATED: %s" % s
    shutil.rmtree(work, ignore_errors=True)
    return r


def main():
    rows = con_rows()
    print("issue 3863 -- did `-H` ever print an include trace under `-P`?")
    print("linear sweep of every stable (non-prerelease) release, oldest first,")
    print("plus the ground-truth build. Prereleases are excluded by policy: the")
    print("issue text names none.")
    print()

    results = []
    for tag, exe in rows:
        try:
            results.append(probe(tag, exe))
        except Exception as e:            # a broken release must not hide
            results.append({"tag": tag, "grammar": "??", "alarm": repr(e),
                            "compile_H": False, "p_H": False, "p_Vi": False,
                            "p_H_ran": False, "p_Vi_ran": False,
                            "compile_M": False, "p_M": False,
                            "p_H_rejected": False, "p_Vi_rejected": False,
                            "compile_M_rejected": False,
                            "p_M_rejected": False, "p_H_say": ""})

    hdr = ("%-15s %-4s %-9s %-9s %-8s %-8s %-9s %-6s"
           % ("release", "-P", "compile", "-P ran", "-P +-H", "-P +-Vi",
              "compile", "-P"))
    print(hdr)
    print("%-15s %-4s %-9s %-9s %-8s %-8s %-9s %-6s"
          % ("", "gram", "+-H CTRL", "(pp'd ok)", "trace", "trace", "+-M",
             "+-M"))
    print("-" * len(hdr))
    for r in results:
        print("%-15s %-4s %-9s %-9s %-8s %-8s %-9s %-6s%s"
              % (r["tag"], r.get("grammar", "?"),
                 "yes" if r["compile_H"] else "NO",
                 "yes" if r["p_H_ran"] else "NO",
                 "yes" if r["p_H"] else "no",
                 "yes" if r["p_Vi"] else "no",
                 "yes" if r["compile_M"] else
                 ("rejected" if r["compile_M_rejected"] else "no"),
                 "yes" if r["p_M"] else
                 ("rejctd" if r["p_M_rejected"] else "no"),
                 r.get("alarm", "")))

    usable = [r for r in results if r["compile_H"] and r["p_H_ran"]]
    print()
    print("releases whose positive control fired AND which really preprocessed:"
          " %d of %d" % (len(usable), len(results)))
    print("of those, releases printing an include trace under -P with -H:  %d"
          % sum(1 for r in usable if r["p_H"]))
    print("of those, releases printing an include trace under -P with -Vi: %d"
          % sum(1 for r in usable if r["p_Vi"]))
    print("any release rejected -H/-Vi as an unknown argument under -P:    %s"
          % any(r["p_H_rejected"] or r["p_Vi_rejected"] for r in results))
    print("first release where -M lists dependencies on a normal compile:  %s"
          % next((r["tag"] for r in results if r["compile_M"]), "none"))
    print("any release where -M lists dependencies under -P:               %s"
          % next((r["tag"] for r in results if r["p_M"]), "none"))
    print("any probe mutated its own input evidence:                       %s"
          % (any(r.get("alarm") for r in results) or False))
    print()
    print("verbatim: what `-P ... -H` said, per release")
    for r in results:
        say = r.get("p_H_say", "")
        print("  %-15s exit=%-3s %s" % (r["tag"], r.get("p_H_rc", "?"),
                                        say if say else "(no output at all)"))
    shutil.rmtree(os.path.join(HERE, "work-history"), ignore_errors=True)


def con_rows():
    c = triage.con()
    rows = [(r["tag"], r["cached_path"]) for r in c.execute(
        "SELECT tag, cached_path FROM releases "
        "WHERE prerelease = 0 AND bisectable = 1 "
        "ORDER BY published_at").fetchall()]
    out = []
    for tag, path in rows:
        out.append((tag, path or triage.ensure_release(tag)))
    out.append(("main-debug", triage.resolve_compiler("main-debug")))
    return out


if __name__ == "__main__":
    main()
