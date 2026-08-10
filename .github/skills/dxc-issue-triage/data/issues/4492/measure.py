"""#4492 release matrix: predicate clauses, shader shapes and controls, per release.

Why this exists, and why it is not just `bisect` output.

1. `match.json` is an `all_of` of three clauses, two of which are instrument
   self-tests (does this build emit `rawBufferLoad.f16` at all; does it report
   the `$Element` as 32 bytes).  An `all_of` result hides which clause moved, so
   a release whose disassembler merely renamed or relocated a token would score
   `no-repro` and read exactly like a fix.  Every clause is scored separately on
   every stable release and printed side by side, so an instrument change
   cannot masquerade as a behaviour change.

2. The primary `bisect` history is a history of the *reporter's shader*, not of
   the defect.  Measured here: `repro.hlsl` is clean on v1.4.1907 and v1.5.2010
   because those builds load the whole 32-byte struct up front and resolve the
   switch from registers, never reaching the per-element buffer-load path.  The
   same source cut down to the issue body's own snippet (`minimal-matrix.hlsl`)
   reaches that path on every release and is wrong on every release.  Running
   both shapes on every release is the only way that distinction is visible.

3. The negative controls run on every release too, not just ground truth: a
   predicate that fires on correct f16 structured-buffer IR would be worthless,
   and "worthless on this build only" is a real possibility across 20 releases.

Each shader is scored against the predicate whose instrument it actually uses.
A store-only shader emits no `rawBufferLoad.f16`, so scoring it with
`match.json` would produce a no-match for an instrument reason rather than a
behavioural one; `match-store.json` is the same test rebuilt around
`rawBufferStore.f16`.  Both clause sets are printed for every row anyway, so
nothing is hidden by that routing.

Self-consistency: every row asserts that it parsed at least one f16 buffer
access out of a run that exited 0.  If the reader ever stops matching -- LLVM's
printer changing spacing, an operand gaining a type -- the row says
`4492-PARSE-WARNING` loudly instead of quietly reporting an empty offset list,
which would look like "nothing was accessed" rather than "nothing was read".

Run:  python measure.py            (from this issue's directory)
Writes: manual-case-release-matrix.txt
"""

import os
import re
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SKILL_DIR)))
DB = os.path.join(SKILL_DIR, ".cache", "triage.db")

GROUND_TRUTH = os.path.join(REPO_ROOT, "build", "Debug", "bin", "dxc.exe")

ARGS = ["-T", "cs_6_2", "-E", "testStructuredBufferMatrixLoad2",
        "-enable-16bit-types"]

ELEMENT_BYTES = 32

# (role, shader, predicate, what a correct build must produce)
SHADERS = [
    ("repro", "repro.hlsl", "match.json",
     "the reporter's attached shader, verbatim; correct span <= 32"),
    ("minimal", "minimal-matrix.hlsl", "match.json",
     "the issue body's own snippet, a[0].xy + a[3].zw; correct 0,2,28,30"),
    ("ld-ctrl", "control-half-vec-array.hlsl", "match.json",
     "NEGATIVE CONTROL for match.json: half4 v[4]; correct 0,2,...,30"),
    ("store", "store-matrix.hlsl", "match-store.json",
     "store direction, a[0][1] and a[3][3]; correct 2 and 30"),
    ("st-ctrl", "control-store-half-vec-array.hlsl", "match-store.json",
     "NEGATIVE CONTROL for match-store.json: half4 v[4]; correct 2 and 30"),
]

# Clause regexes, kept textually identical to the two predicate files so a
# divergence between this table and a `reindex` is visible rather than assumed.
CLAUSE_ELEMSIZE = re.compile(r"\$Element;\s+; Offset:\s+0 Size:\s+32\b")
OFFSET_OOB = r"i32 [^,]+, i32 (?:3[2-9]|[4-9][0-9]|[1-9][0-9]{2,})[,)]"
CLAUSES = {
    "match.json": (
        re.compile(r"@dx\.op\.rawBufferLoad\.f16\("),
        re.compile(r"@dx\.op\.rawBufferLoad\.f16\(i32 \d+, "
                   r"%dx\.types\.Handle %[\w.]+, " + OFFSET_OOB)),
    "match-store.json": (
        re.compile(r"@dx\.op\.rawBufferStore\.f16\("),
        re.compile(r"@dx\.op\.rawBufferStore\.f16\(i32 \d+, "
                   r"%dx\.types\.Handle %[\w.]+, " + OFFSET_OOB)),
}

# Reader for the observation, deliberately looser than the symptom clauses: it
# reports every access, load or store, at every offset.
ACCESS = re.compile(
    r"@dx\.op\.rawBuffer(Load|Store)\.f16\(i32 \d+, %dx\.types\.Handle %[\w.]+, "
    r"i32 [^,]+, i32 (\d+).*?i8 (\d+), i32 \d+\)")


def rel(path):
    """Repo-relative display path, so committed output is machine-independent."""
    try:
        return "<repo>/" + os.path.relpath(path, REPO_ROOT).replace("\\", "/")
    except ValueError:
        return path


def releases():
    """Stable releases with a cached dxc, oldest build first.

    Prereleases are excluded to match `bisect`'s policy; they are named in the
    header so the exclusion is visible rather than silent.
    """
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT tag, prerelease, build_date, cached_path FROM releases "
        "WHERE cached_path IS NOT NULL ORDER BY build_date").fetchall()
    con.close()
    stable = [(r["tag"], r["cached_path"]) for r in rows if not r["prerelease"]]
    skipped = [r["tag"] for r in rows if r["prerelease"]]
    return stable, skipped


def observe(text):
    return [(kind, int(off), int(mask))
            for kind, off, mask in ACCESS.findall(text)]


def fmt(accesses):
    if not accesses:
        return "(none)"
    return " ".join(f"{'ld' if k == 'Load' else 'st'}{o}/m{m}"
                    for k, o, m in accesses)


def span(accesses):
    """Highest byte touched, so 'past the element' is a number, not a claim."""
    hi = 0
    for _, off, mask in accesses:
        hi = max(hi, off + 2 * bin(mask).count("1"))
    return hi


def main():
    stable, skipped = releases()
    out = []
    w = out.append

    w("#4492 release matrix -- predicate clauses, shader shapes, raw offsets")
    w("")
    w("Generated by measure.py (committed beside this file); every command below")
    w("is echoed exactly as executed, via subprocess.list2cmdline.")
    w("")
    w(f"args (identical for every shader and every release): "
      f"{subprocess.list2cmdline(ARGS)}")
    w("")
    for role, shader, pred, what in SHADERS:
        w(f"  {role:<9}{shader:<34}{pred:<18}{what}")
    w("")
    w(f"Every shader declares a {ELEMENT_BYTES}-byte $Element. Correct codegen "
      "keeps every")
    w("rawBufferLoad/Store.f16 inside [0,32). 'span' is the highest byte touched,")
    w("computed as offset + 2 * popcount(mask), so 'past the end' is a number.")
    w("")
    w("Both predicates are an AND of three clauses:")
    w("  A = anchor/self-test: the f16 buffer op the predicate reads is present")
    w("  E = element-size self-test: $Element reported as 32 bytes")
    w("  S = symptom: some such op has elementOffset >= 32")
    w("A and E are the instrument. If either flips while S does not, that")
    w("release is unmeasurable under that predicate, NOT clean. Both clause sets")
    w("are shown for every row; 'scored' marks the one that shader is judged by.")
    w("")
    w(f"prereleases excluded from the sequence by policy: {', '.join(skipped)}")
    w("")

    targets = list(stable) + [("main-debug", GROUND_TRUTH)]

    warnings = 0
    rows = []
    for tag, exe in targets:
        if not os.path.exists(exe):
            w(f"## {tag}: SKIPPED, no executable at {rel(exe)}")
            continue
        w(f"## {tag}")
        w(f"[exe] {rel(exe)}")

        rec = {"tag": tag}
        for role, shader, pred, _ in SHADERS:
            argv = [exe] + ARGS + [shader]
            p = subprocess.run(argv, cwd=HERE, capture_output=True, text=True,
                               timeout=180)
            text = (p.stdout or "") + (p.stderr or "")
            acc = observe(text)
            e = bool(CLAUSE_ELEMSIZE.search(text))
            w(f"$ {subprocess.list2cmdline([rel(argv[0])] + argv[1:])}")
            w(f"  role={role}  exit={p.returncode}  scored by {pred}")
            verdict = None
            for name, (anchor, symptom) in CLAUSES.items():
                a = bool(anchor.search(text))
                s = bool(symptom.search(text))
                hit = a and e and s
                w(f"  {'scored ' if name == pred else '       '}"
                  f"{name:<17} A={int(a)} E={int(e)} S={int(s)}"
                  f"  -> {'MATCH' if hit else 'no-match'}")
                if name == pred:
                    verdict = hit
            w(f"  f16 accesses (offset/mask): {fmt(acc)}")
            sp = span(acc)
            w(f"  span: {sp} bytes into a {ELEMENT_BYTES}-byte $Element"
              + ("  <-- PAST THE END OF THE ELEMENT"
                 if sp > ELEMENT_BYTES else ""))
            if p.returncode == 0 and not acc:
                w("  4492-PARSE-WARNING: exit 0 but 0 f16 buffer accesses"
                  " parsed. The reader, not the compiler, may be what changed.")
                warnings += 1
            rec[role] = {"match": verdict, "span": sp, "n": len(acc)}
        rows.append(rec)
        w("")

    hdr = f"{'release':<16}" + "".join(f"{r:<11}" for r, _, _, _ in SHADERS)

    w("## summary -- span in bytes into a 32-byte element ('!' = past the end)")
    w("")
    w(hdr)
    for r in rows:
        line = f"{r['tag']:<16}"
        for role, _, _, _ in SHADERS:
            sp = (r.get(role) or {}).get("span", 0)
            line += f"{str(sp) + ('!' if sp > ELEMENT_BYTES else ''):<11}"
        w(line)
    w("")
    w("## summary -- verdict under each shader's own predicate")
    w("")
    w(hdr)
    for r in rows:
        line = f"{r['tag']:<16}"
        for role, _, _, _ in SHADERS:
            d = r.get(role) or {}
            line += f"{('MATCH' if d.get('match') else 'no-match'):<11}"
        w(line)
    w("")
    w("Read the summary this way:")
    w("  ld-ctrl / st-ctrl  must be no-match with span 32 on EVERY release.")
    w("           They are the negative controls; a MATCH in either column")
    w("           invalidates the predicate it belongs to.")
    w("  repro    is the reporter's shader. Clean on v1.4.1907 and v1.5.2010")
    w("           only because those builds load the whole struct up front,")
    w("           so the per-element path the defect lives in is never used.")
    w("  minimal  is the issue body's own snippet and is wrong on every")
    w("           release, which is what says the defect is older than the")
    w("           v1.6.2104 boundary the reporter's shader shows.")
    w("  store    is the write direction: the same doubled stride, so the")
    w("           store lands in the NEXT buffer element. Adjacent to the")
    w("           issue, which is about loads, and not part of the verdict.")
    w("")
    w(f"4492-PARSE-WARNINGS: {warnings}")

    text = "\n".join(out) + "\n"
    dest = os.path.join(HERE, "manual-case-release-matrix.txt")
    with open(dest, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(text)
    print(f"wrote {rel(dest)}")
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
