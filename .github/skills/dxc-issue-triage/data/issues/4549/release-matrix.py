"""Per-release control matrix for #4549.

`bisect` runs one command (cmd.txt) against each release. Three things it cannot
answer on its own here, all of which SKILL.md requires:

  * whether a release that did not reproduce could have -- the feature-presence
    control, run on *every* release rather than only on ground truth;
  * whether the register class written in the source is honoured, which is the
    behavioural half of the report and involves no diagnostic text at all;
  * whether the release's own register-class diagnostic exists, which is the
    self-test for the primary predicate's absence clause.

It also runs a lib_6_3 restatement, because RayQuery/ps_6_5 is Shader Model 6.5
and cannot be expressed by the two oldest stable releases.

Prereleases are excluded: the issue names none, so policy keeps them out
(SKILL.md, step 6). Every command is printed with subprocess.list2cmdline, so
the transcript states what actually ran rather than what someone typed.

    python release-matrix.py > manual-case-release-matrix.txt
"""

import os
import re
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "scripts")))
import triage  # noqa: E402

CASES = [
    ("repro",         ["-T", "ps_6_5", "-E", "main", "repro.hlsl"]),
    ("as-srv-ctrl",   ["-T", "ps_6_5", "-E", "main", "control-as-srv-register.hlsl"]),
    ("as-u0-alone",   ["-T", "ps_6_5", "-E", "main", "control-as-u0-alone.hlsl"]),
    ("sbuf-u0-ctrl",  ["-T", "ps_6_5", "-E", "main", "control-sbuf-u0.hlsl"]),
    ("lib63-repro",   ["-T", "lib_6_3", "translation-lib63.hlsl"]),
    ("lib63-ctrl",    ["-T", "lib_6_3", "control-lib63-srv-register.hlsl"]),
    ("lib63-u0-alone", ["-T", "lib_6_3", "control-lib63-as-u0-alone.hlsl"]),
]

BIND_ROW = re.compile(r"(?m)^;\s*opaque_as\s+\S+.*?(?<![\w])([tu]\d+)(?![\w])")
BLAMES_INNOCENT = re.compile(
    r"(?m)^[^\n]*\bdepth_buffer\b[^\n]*\b(?:register|space)\s+\d")
REGISTER_DIAG = re.compile(r"(?i)invalid register specification")
NO_FEATURE = re.compile(
    r"(?i)(use of undeclared identifier|unknown type name|no member named"
    r"|invalid profile|is not supported for target profile"
    r"|no matching function for call to)")


def run(exe, args):
    p = subprocess.run([exe] + args, cwd=HERE, capture_output=True, text=True,
                       errors="replace", timeout=300)
    out = triage.redact_paths((p.stdout or "") + (p.stderr or ""))
    return p.returncode & 0xFFFFFFFF, out


def summarise(name, code, out):
    """One token per cell, chosen so a reader can re-derive it from the transcript."""
    if NO_FEATURE.search(out):
        return "no-feature"
    if triage.is_internal_failure(out, code, False):
        return "INTERNAL-FAILURE"
    if name in ("repro", "lib63-repro"):
        if BLAMES_INNOCENT.search(out) and not REGISTER_DIAG.search(out):
            return "blames-depth_buffer"
        if REGISTER_DIAG.search(out):
            return "register-diagnostic"
        return "clean" if code == 0 else "other-error"
    if name in ("as-u0-alone", "lib63-u0-alone"):
        m = BIND_ROW.search(out)
        return f"bound-at-{m.group(1)}" if m else ("clean-no-row" if code == 0
                                                   else "error")
    if name == "sbuf-u0-ctrl":
        return "register-diagnostic" if REGISTER_DIAG.search(out) else (
            "clean" if code == 0 else "other-error")
    return "clean" if code == 0 else "error"


def selftest():
    """Prove the classifier can tell a complaint from an echo of the source.

    BLAMES_INNOCENT deliberately does not require the word `error`, because
    v1.4.1907's validator prints its message without one. The risk that buys is
    matching a clang caret line that echoes depth_buffer's own declaration, so
    assert here that it does not -- a harness that can return 'nothing here' and
    'nothing matched' through the same channel will eventually be believed.
    """
    src = open(os.path.join(HERE, "repro.hlsl"), encoding="utf-8").read()
    real = ("error: resource depth_buffer at register 0 overlaps with "
            "resource opaque_as at register 0, space 0")
    validator = ("Resource depth_buffer with base 0 size 1 overlap with other "
                 "resource with base 0 size 1 in space 0")
    ok = (not BLAMES_INNOCENT.search(src)
          and BLAMES_INNOCENT.search(real)
          and BLAMES_INNOCENT.search(validator))
    print(f"# selftest: blame-detector rejects the repro source and accepts "
          f"both real message forms: {'pass' if ok else 'FAIL'}")
    if not ok:
        print("# 4549: PARSE-WARNING: blame detector is not discriminating")


def main():
    con = sqlite3.connect(triage.DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT tag, cached_path, build_date FROM releases "
        "WHERE cached_path IS NOT NULL AND prerelease = 0 "
        "ORDER BY build_date").fetchall()
    skipped = [r["tag"] for r in con.execute(
        "SELECT tag FROM releases WHERE cached_path IS NOT NULL "
        "AND prerelease = 1 ORDER BY build_date")]
    ground = con.execute(
        "SELECT id, exe_path FROM compilers WHERE id = 'main-debug'").fetchone()

    builds = [(r["tag"], r["cached_path"], r["build_date"]) for r in rows]
    builds.append((ground["id"], ground["exe_path"], ""))

    print("# per-release control matrix for #4549")
    print("# generated by release-matrix.py; every command below is printed "
          "with subprocess.list2cmdline")
    print("# prereleases excluded by policy (issue names none): "
          + ", ".join(skipped))
    selftest()
    print()

    table = []
    for tag, exe, date in builds:
        vcode, vout = run(exe, ["--version"])
        version = " | ".join(ln.strip() for ln in vout.splitlines() if ln.strip())
        print("=" * 78)
        print(f"## {tag}   build_date={date or 'n/a'}")
        print(f"$ {subprocess.list2cmdline([triage.display_exe(exe), '--version'])}")
        print(f"[exit] {vcode}")
        print(version)
        cells = {}
        for name, args in CASES:
            code, out = run(exe, args)
            cells[name] = summarise(name, code, out)
            print()
            print(f"--- {name} ---")
            print(f"$ {subprocess.list2cmdline([triage.display_exe(exe)] + args)}")
            print(f"[exit] {code} ({code:#010x})")
            body = out.strip()
            if name in ("as-u0-alone", "lib63-u0-alone") and code == 0:
                keep = [ln for ln in body.splitlines()
                        if "Resource Bindings" in ln or re.match(r"^;\s*(opaque_as|Name|-+)", ln)]
                body = "\n".join(keep) if keep else "(compiled; no binding table row)"
            elif code == 0 and len(body.splitlines()) > 6:
                body = "(compiled successfully; disassembly elided)"
            print(body if body else "(no output)")
            print(f"=> {cells[name]}")
        table.append((tag, cells))
        print()

    print("=" * 78)
    print("## summary")
    hdr = ["build"] + [n for n, _ in CASES]
    widths = [max(len(h), *(len(str(r[0])) if i == 0 else len(r[1][h])
                            for r in table)) for i, h in enumerate(hdr)]
    print("  ".join(h.ljust(w) for h, w in zip(hdr, widths)))
    for tag, cells in table:
        print("  ".join(
            (tag if i == 0 else cells[h]).ljust(w)
            for i, (h, w) in enumerate(zip(hdr, widths))))


if __name__ == "__main__":
    main()
