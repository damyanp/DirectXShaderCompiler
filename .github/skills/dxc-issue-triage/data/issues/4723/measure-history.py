"""#4723: date the behaviour across shipped releases.

`triage.py bisect` refuses to drive a harness (`refuse_harness_bisect`: the
registered exe is not named dxc.exe), and rightly so -- it would have no way to
tell a harness bug from a compiler change. But the question "has this ever
worked?" still has to be answered, so this walks the cached releases directly
and applies the same measurement the scored captures apply.

Three things this has to get right, and each of them is a trap the naive
version falls into:

* **`-P` changed spelling inside the window.** Until 8bf2b087c (PR #4624,
  first shipped in v1.7.2212) `-P` was a Separate option that took the output
  filename: `dxc -P out.i src.hlsl`. After it, `-P` is a flag and the output
  name comes from `-Fi`. Probing only the modern spelling would report "no
  preprocessed output" for every release before 2022-12 and invite the
  conclusion that -P itself regressed. Both spellings are tried on every
  release and the report records which one worked.

* **Every release gets a positive control.** A release that cannot compile the
  shader at all, or that does not know `-MF` in ordinary compile mode, cannot
  say anything about `-MF` under `-P`. The control is the compile-mode depfile
  itself, so "the depfile is missing under -P" is only ever recorded for a
  release that demonstrably writes one without -P.

* **Prereleases are excluded.** #4723 is not filed against one (the body names
  no version at all), so per SKILL.md they stay out of the history.

Artifacts go in a per-release working directory that this script creates, so
nothing can be confused with a file another release wrote, and a directory git
cannot store (git does not track empty directories) cannot make a re-run look
like a failure. The directory is removed when the run finishes; the report is
the deliverable.
"""

import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *([os.pardir] * 6)))
SKILL_SCRIPTS = os.path.join(REPO, ".github", "skills", "dxc-issue-triage",
                             "scripts")
sys.path.insert(0, SKILL_SCRIPTS)
import triage  # noqa: E402

WORK = os.path.join(HERE, "history-work")
REPORT = os.path.join(HERE, "manual-case-release-history.txt")
SHADER = "repro.hlsl"
DEP_RULE = re.compile(r"^repro\.hlsl:\s+repro\.hlsl\s*\\?\s*$")


def run(exe, args):
    p = subprocess.run([exe] + args, cwd=HERE, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode & 0xFFFFFFFF, triage.redact_paths(
        (p.stdout or "") + (p.stderr or ""))


def size(path):
    return os.path.getsize(path) if os.path.isfile(path) else None


def tail_is_dep_rule(path):
    """True if the file ends in a make rule naming the shader."""
    if not os.path.isfile(path):
        return False
    with open(path, encoding="utf-8", errors="replace") as f:
        body = [ln.strip() for ln in f if ln.strip()]
    return bool(body) and any(DEP_RULE.match(ln) for ln in body[-3:])


def fresh(tag):
    d = os.path.join(WORK, re.sub(r"[^A-Za-z0-9._-]", "_", tag))
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)
    return d


def rel(d, name):
    return os.path.relpath(os.path.join(d, name), HERE).replace(os.sep, "/")


def measure(tag, exe, out):
    """One release. Returns (row dict, transcript lines)."""
    log = []
    row = {"tag": tag}

    def step(title, args):
        rc, text = run(exe, args)
        log.append(f"  $ dxc {subprocess.list2cmdline(args)}")
        log.append(f"    exit=0x{rc:08X}")
        for ln in [x for x in text.splitlines() if x.strip()][:4]:
            log.append(f"    | {ln}")
        return rc

    rc, ver = run(exe, ["--version"])
    row["version"] = " ".join(ver.split())[:60] if rc == 0 else "?"

    # Control 1: can this release compile the shader at all?
    obj = rel(out, "control.dxo")
    step("compile", ["-T", "ps_6_0", "-E", "main", "-Fo", obj, SHADER])
    row["compiles"] = size(os.path.join(HERE, obj)) is not None

    # Control 2: does it write a depfile in ordinary compile mode?
    dep = rel(out, "compile.d")
    step("compile+MF", ["-T", "ps_6_0", "-E", "main", "-MF", dep, SHADER])
    row["mf_compile"] = size(os.path.join(HERE, dep))

    # Subject, modern spelling: -P is a flag, output named by -Fi.
    inew, dnew = rel(out, "new.i"), rel(out, "new.d")
    step("P(new)+MF", ["-T", "ps_6_0", "-E", "main", "-P", "-Fi", inew,
                       "-MF", dnew, SHADER])
    row["i_new"] = size(os.path.join(HERE, inew))
    row["d_new"] = size(os.path.join(HERE, dnew))

    # Subject, pre-8bf2b087c spelling: -P takes the output filename.
    iold, dold = rel(out, "old.i"), rel(out, "old.d")
    step("P(old)+MF", ["-T", "ps_6_0", "-E", "main", "-P", iold,
                       "-MF", dold, SHADER])
    row["i_old"] = size(os.path.join(HERE, iold))
    row["d_old"] = size(os.path.join(HERE, dold))

    # Baseline for the size comparison: -P with no depfile flag at all.
    for spell, name in (("new", "plain-new.i"), ("old", "plain-old.i")):
        path = rel(out, name)
        args = (["-P", "-Fi", path] if spell == "new" else ["-P", path])
        step(f"P({spell})", ["-T", "ps_6_0", "-E", "main"] + args + [SHADER])
        row["plain_" + spell] = size(os.path.join(HERE, path))

    # Which spelling produced preprocessed output, and was it contaminated?
    row["spelling"] = ("new" if row["i_new"] else
                       "old" if row["i_old"] else None)
    sub = inew if row["spelling"] == "new" else iold
    row["i_bytes"] = row["i_new"] if row["spelling"] == "new" else row["i_old"]
    row["plain_bytes"] = row["plain_" + row["spelling"]] \
        if row["spelling"] else None
    row["depfile_under_p"] = bool(row["d_new"] or row["d_old"])
    row["contaminated"] = tail_is_dep_rule(os.path.join(HERE, sub)) \
        if row["spelling"] else False

    # And does the release accept its own preprocessed output back?
    if row["spelling"]:
        rc = step("recompile", ["-T", "ps_6_0", "-E", "main", sub])
        row["recompile"] = f"0x{rc:08X}"
    else:
        row["recompile"] = "n/a"
    return row, log


def verdict(row):
    if not row["compiles"]:
        return "SKIP -- release cannot compile the repro (control failed)"
    if not row["mf_compile"]:
        return "SKIP -- release has no -MF in compile mode (control failed)"
    if not row["spelling"]:
        return "SKIP -- neither -P spelling produced preprocessed output"
    bits = ["depfile under -P: " + ("WRITTEN" if row["depfile_under_p"]
                                    else "MISSING")]
    bits.append("preprocessed output: "
                + ("CONTAMINATED" if row["contaminated"] else "clean"))
    bits.append("recompiles: " + ("no (" + row["recompile"] + ")"
                                  if row["recompile"] not in ("0x00000000",
                                                              "n/a")
                                  else "yes"))
    return "; ".join(bits)


def main():
    c = triage.con()
    rows = c.execute(
        "SELECT tag, published_at, cached_path FROM releases "
        "WHERE prerelease = 0 AND cached_path IS NOT NULL "
        "ORDER BY published_at").fetchall()
    targets = [(r["tag"], r["published_at"][:10], r["cached_path"])
               for r in rows]
    targets.append(("ground truth (13730886e)", "HEAD",
                    os.path.join(REPO, "build", "Debug", "bin", "dxc.exe")))
    # Probing both -P spellings necessarily mis-parses one of them, and a
    # mis-parse can write a file: on a release where -P still takes a value,
    # `-P -Fi new.i` writes the preprocessed text to a file literally named
    # `-Fi` in the issue directory. Anything the sweep leaves behind up here
    # is removed at the end, so the committed directory holds only the report.
    before = set(os.listdir(HERE))

    out_lines = [
        "#4723 -- release history for `-M`/`-MD`/`-MF` under `-P`",
        "",
        "Generated by measure-history.py. Each release is measured with the",
        "same repro.hlsl the scored captures use, in its own working",
        "directory, with two positive controls and BOTH spellings of -P.",
        "Prereleases are excluded: #4723 names no version, so per SKILL.md",
        "only shipped releases count.",
        "",
    ]
    table, detail = [], []
    for tag, when, exe in targets:
        if not os.path.isfile(exe):
            table.append((tag, when, "SKIP -- not cached locally"))
            continue
        out = fresh(tag)
        row, log = measure(tag, exe, out)
        table.append((tag, when, verdict(row)))
        detail.append(f"=== {tag} ({when})")
        detail.append(f"  dxc --version: {row['version']}")
        detail.append(f"  -P spelling that worked: {row['spelling'] or 'none'}")
        detail.append(f"  preprocessed bytes: {row['i_bytes']} with -MF "
                      f"vs {row['plain_bytes']} without")
        detail.extend(log)
        detail.append("")
        print(f"{tag:28s} {verdict(row)}")

    width = max(len(t) for t, _, _ in table)
    out_lines.append("SUMMARY")
    for tag, when, v in table:
        out_lines.append(f"  {tag:<{width}}  {when}  {v}")
    out_lines += ["", "TRANSCRIPTS", ""] + detail
    with open(REPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write(triage.redact_paths("\n".join(out_lines)) + "\n")
    shutil.rmtree(WORK, ignore_errors=True)
    for name in sorted(set(os.listdir(HERE)) - before):
        path = os.path.join(HERE, name)
        if os.path.isfile(path) and path != REPORT:
            os.remove(path)
            print("cleaned up stray " + name)
    print("wrote " + os.path.basename(REPORT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
