"""#4415 release matrix: does shipping DXC accept the invalid handle too?

`triage.py bisect --linear` answers the *front end* question (does a release's
dxc.exe compile repro.hlsl without a validation error). It cannot answer the
*validator* question for a third-party producer, because bisect drives
`dxc.exe` and the doctored-module probe needs `dxv.exe`.

This script answers both, per release, using only that release's own binaries:

  1. `dxc --version`                       -- name the binary in the capture
  2. compile control-checked-op.hlsl       -- FEATURE-PRESENCE control. A
                                              release that cannot compile a
                                              trivial ps_6_6 texture load never
                                              reached the code under test, so
                                              its row is `invalid-probe`, not
                                              evidence.
  3. compile repro.hlsl                    -- the issue's own shader
  4. if the release ships dxv.exe:
       a. doctor that release's OWN valid module -> annotateHandle res operand
          becomes `zeroinitializer`, and run that release's dxv on it. This is
          the third-party-producer probe: no ground-truth binary is involved
          and the module asks for that release's own validator version.
       b. doctor that release's OWN checked-opcode module -> textureLoad handle
          becomes `zeroinitializer`, and run that release's dxv on it. This is
          the VALIDATOR-LIVENESS control: it must FAIL. A release whose dxv
          accepts (a) and also accepts (b) is not evidence of a gap -- it is
          evidence that the probe never reached a working validator.

Every command is echoed before it runs and every patch asserts its occurrence
count, so this file can be re-derived rather than trusted.

Run from this directory:
    python release-matrix.py > manual-case-release-matrix.txt
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# <repo>/.github/skills/dxc-issue-triage/data/issues/4415/ -> <repo>
REPO = os.path.abspath(os.path.join(HERE, *([os.pardir] * 6)))
SKILL = os.path.join(REPO, ".github", "skills", "dxc-issue-triage")

# Captured output is normalised with triage.py's own redact_paths() rather than
# a second implementation of the same rule: it tokenises the checkout root, the
# triage root and the release cache, matching either separator, repeated
# separators and any case. A local `text.replace(REPO, ...)` gets the common
# case and silently misses the rest.
sys.path.insert(0, os.path.join(SKILL, "scripts"))
import triage  # noqa: E402

# Two roots hold unpacked releases on a machine that has run the lit release
# tests: the triage cache, and the release archives the test suite unpacks.
# Looking in only one silently reports "not-cached" for releases that are in
# fact present, which would put holes in the matrix that are not real.
RELEASE_ROOTS = [
    os.path.join(SKILL, ".cache", "compilers", "releases"),
    os.path.join(REPO, "build", "tools", "clang", "test", "dxc_releases"),
]
OUTDIR = os.path.join(HERE, "release-modules")

ANNOT_RE = re.compile(
    r"@dx\.op\.annotateHandle\(i32 216, %dx\.types\.Handle ([^,]+),")
TEXLOAD_RE = re.compile(
    r"@dx\.op\.textureLoad\.f32\(i32 66, %dx\.types\.Handle ([^,]+),")

# Releases predate the ground-truth build, so they emit older validator
# versions; each release's module is built by that release's own dxc, so the
# valver always matches the dxv it is handed to.
ORDER = ["v1.4.1907", "v1.5.2010", "v1.6.2104", "v1.6.2106", "v1.6.2112",
         "v1.7.2207", "v1.7.2212", "v1.7.2212.1", "v1.7.2308", "v1.8.2403",
         "v1.8.2403.1", "v1.8.2403.2", "v1.8.2405", "v1.8.2407", "v1.8.2502",
         "v1.8.2505", "v1.8.2505.1", "v1.9.2602", "v1.9.2602.24", "v1.9.2607"]


def display(path):
    return triage.redact_paths(os.path.abspath(path)).replace(os.sep, "/")


def run(argv, cwd=HERE, quiet_stdout=False):
    # Every element goes through display(), not just argv[0]: the -Fc output
    # paths are absolute, and echoing them raw bakes one machine's layout into
    # a committed capture (scripts/check_paths.py rejects it).
    print("$ " + subprocess.list2cmdline(
        [display(a) if os.path.isabs(a) else a for a in argv]))
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = p.stdout if not quiet_stdout else ""
    text = triage.redact_paths((out + p.stderr).strip())
    if text:
        print("\n".join("  " + ln for ln in text.splitlines()))
    print("  [exit] 0x%08X" % (p.returncode & 0xFFFFFFFF))
    return p


def find(version, name):
    """x64 `name` for `version`, whichever cache root and layout holds it."""
    for root in RELEASE_ROOTS:
        base = os.path.join(root, version)
        if not os.path.isdir(base):
            continue
        for dirpath, _dirs, files in os.walk(base):
            if name in files and os.path.basename(dirpath).lower() == "x64":
                return os.path.join(dirpath, name)
        cand = os.path.join(base, name)
        if os.path.isfile(cand):
            return cand
    return None


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def patch(src, dst, rx, spelling, why):
    """Replace the operand matched by `rx` with `spelling`; assert it moved."""
    text = read(src)
    hits = rx.findall(text)
    print("  ---- %s: %s" % (os.path.basename(dst), why))
    print("  [patch] %d call site(s), operand(s)=%s"
          % (len(hits), [h.strip() for h in hits]))
    if len(hits) != 1:
        print("  [PATCH-WARNING] expected exactly 1, found %d -- module NOT "
              "written; any row naming it is measuring nothing" % len(hits))
        return None
    if hits[0].strip() in ("undef", "zeroinitializer", "null"):
        print("  [PATCH-WARNING] base module was already invalid")
        return None
    out = rx.sub(lambda m: m.group(0).replace(m.group(1), " " + spelling, 1),
                 text, count=1)
    if out == text:
        print("  [PATCH-WARNING] substitution changed nothing")
        return None
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    check = rx.findall(out)
    print("  [patched] operand(s) now %s" % [h.strip() for h in check])
    if [h.strip() for h in check] != [spelling]:
        print("  [PATCH-WARNING] operand did not become %r" % spelling)
        return None
    return dst


def dxv_verdict(dxv, module):
    p = run([dxv, os.path.basename(module)], cwd=OUTDIR)
    return "ACCEPTED" if p.returncode == 0 else "REJECTED"


def main():
    if not any(os.path.isdir(r) for r in RELEASE_ROOTS):
        sys.exit("no release cache under %s"
                 % " or ".join(display(r) for r in RELEASE_ROOTS))
    os.makedirs(OUTDIR, exist_ok=True)

    rows = []
    for version in ORDER:
        print("\n" + "=" * 72)
        print("== %s" % version)
        print("=" * 72)
        dxc = find(version, "dxc.exe")
        if not dxc:
            print("  [skip] no x64 dxc.exe cached")
            rows.append((version, "not-cached", "-", "-"))
            continue
        run([dxc, "--version"])

        # (2) FEATURE-PRESENCE control, and the base module for the dxv probe.
        checked = os.path.join(OUTDIR, "%s-checkedop.ll" % version)
        p = run([dxc, "-T", "ps_6_6", "-E", "main", "control-checked-op.hlsl",
                 "-Fc", checked], quiet_stdout=True)
        if p.returncode != 0:
            print("  [feature-presence] FAILED -- this release cannot compile "
                  "a trivial ps_6_6 texture load, so it never reached the code "
                  "under test. Row is invalid-probe, not evidence.")
            rows.append((version, "invalid-probe", "-", "-"))
            continue
        print("  [feature-presence] ok (ps_6_6 texture load compiles)")

        # (3) the issue's own shader through this release's front end
        print("\n  -- repro.hlsl (the issue's shader), this release's dxc --")
        emitted = os.path.join(OUTDIR, "%s-emitted.ll" % version)
        p = run([dxc, "-T", "vs_6_6", "-E", "main", "repro.hlsl",
                 "-Fc", emitted], quiet_stdout=True)
        if p.returncode != 0:
            front = "rejected"
            if "invalid profile" in p.stderr or "undeclared identifier" in p.stderr:
                front = "invalid-probe"
        else:
            text = read(emitted) if os.path.isfile(emitted) else ""
            bad = [h.strip() for h in ANNOT_RE.findall(text)
                   if h.strip() in ("undef", "zeroinitializer", "null")]
            print("  [emitted] annotateHandle res operands=%s"
                  % [h.strip() for h in ANNOT_RE.findall(text)])
            front = "accepted+invalid-handle" if bad else "accepted"

        # (4) third-party-producer probe, only where dxv.exe shipped
        dxv = find(version, "dxv.exe")
        if not dxv:
            print("\n  [dxv] this release ships no dxv.exe -- validator probe "
                  "not possible from shipping bits alone")
            rows.append((version, "ok", front, "no dxv shipped"))
            continue

        print("\n  -- doctored modules, this release's own dxc + dxv --")
        valid = os.path.join(OUTDIR, "%s-valid.ll" % version)
        p = run([dxc, "-T", "vs_6_6", "-E", "main", "control-valid.hlsl",
                 "-Fc", valid], quiet_stdout=True)
        if p.returncode != 0:
            print("  [PATCH-WARNING] control-valid.hlsl did not compile here")
            rows.append((version, "ok", front, "base module unavailable"))
            continue

        subj = patch(valid, os.path.join(OUTDIR, "%s-zeroinit.ll" % version),
                     ANNOT_RE, "zeroinitializer",
                     "SUBJECT: annotateHandle res operand -> zeroinitializer")
        ctrl = patch(checked,
                     os.path.join(OUTDIR, "%s-checkedop-zeroinit.ll" % version),
                     TEXLOAD_RE, "zeroinitializer",
                     "LIVENESS CONTROL, must be REJECTED: the same operand "
                     "value on textureLoad")
        if not subj or not ctrl:
            rows.append((version, "ok", front, "module generation failed"))
            continue

        subj_v = dxv_verdict(dxv, subj)
        ctrl_v = dxv_verdict(dxv, ctrl)
        print("  [dxv] annotateHandle+zeroinitializer -> %s" % subj_v)
        print("  [dxv] textureLoad+zeroinitializer    -> %s (must be REJECTED)"
              % ctrl_v)
        if ctrl_v != "REJECTED":
            print("  [CONTROL-WARNING] the liveness control was accepted, so "
                  "this release's row proves nothing about annotateHandle")
            rows.append((version, "ok", front, "control failed - void"))
            continue
        rows.append((version, "ok", front, "dxv %s" % subj_v))

    print("\n" + "=" * 72)
    print("== summary")
    print("=" * 72)
    print("  %-14s %-14s %-24s %s"
          % ("release", "probe", "dxc on repro.hlsl", "dxv on doctored module"))
    for r in rows:
        print("  %-14s %-14s %-24s %s" % r)
    print("\n  'accepted+invalid-handle' = compiled with exit 0 AND the emitted")
    print("  module contains annotateHandle with an undef/zeroinitializer res")
    print("  operand, i.e. this release's own validator passed it.")


if __name__ == "__main__":
    main()
