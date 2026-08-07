"""#2128 -- measure how well dxc's and fxc's shader objects compress.

The issue's claim is a *ratio*, which the triage framework's predicate vocabulary (exit codes
and output text) cannot express. So the falsifiable rule lives in expected.md and is evaluated
here; the output is committed as manual-case-compression.txt.

Ratio = len(raw_deflate(bytes)) / len(bytes), level 9, wbits=-15. Raw deflate is exactly what
a .zip member uses, and a .zip compresses each member independently -- which is the right model
for the reporter's "if I will zip same shaders".

The DXIL container reuses the DXBC container format, so one parser splits both and the per-part
ratios are directly comparable.

Usage:
    python measure.py              dxc vs fxc on the corpus, with a per-part breakdown
    python measure.py --history    whole-file ratio for every cached dxc release

Compiler paths come from the DXC / FXC environment variables, falling back to the repo's Debug
build and to the newest fxc.exe in the Windows SDK. Nothing is hardcoded to one machine, and
the scratch directory is created here rather than assumed -- git does not store empty
directories, and a repro that depends on one fails for an unrelated reason (see #2427).
"""

import glob
import hashlib
import json
import os
import subprocess
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REPO = os.path.abspath(os.path.join(SKILL, "..", "..", ".."))
ART = os.path.join(HERE, "artifacts")

CORPUS = ["corpus-small.hlsl", "repro.hlsl", "corpus-large.hlsl"]

DXC_ARGS = ["-T", "ps_6_0", "-E", "main", "-O3"]
FXC_ARGS = ["/T", "ps_5_1", "/E", "main", "/O3", "/nologo"]
STRIP = "-Qstrip_reflect"


def find_dxc():
    return os.environ.get("DXC") or os.path.join(REPO, "build", "Debug", "bin", "dxc.exe")


def find_fxc():
    if os.environ.get("FXC"):
        return os.environ["FXC"]
    pat = r"C:\Program Files (x86)\Windows Kits\10\bin\*\x64\fxc.exe"
    found = sorted(glob.glob(pat))
    return found[-1] if found else None


def deflate(data):
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    return c.compress(data) + c.flush()


def ratio(data):
    return len(deflate(data)) / len(data) if data else float("nan")


def parse_container(data):
    """Split a DXBC/DXIL container into (fourcc, size) parts. Layout from
    include/dxc/DxilContainer/DxilContainer.h: FourCC(4) Hash(16) Version(4)
    ContainerSize(4) PartCount(4), then uint32 PartOffset[PartCount], each pointing at
    a part header of FourCC(4) PartSize(4) followed by PartSize bytes."""
    if len(data) < 32 or data[:4] != b"DXBC":
        return None
    n = int.from_bytes(data[28:32], "little")
    parts = []
    for i in range(n):
        off = int.from_bytes(data[32 + 4 * i:36 + 4 * i], "little")
        cc = data[off:off + 4].decode("ascii", "replace")
        sz = int.from_bytes(data[off + 4:off + 8], "little")
        parts.append((cc, data[off + 8:off + 8 + sz]))
    return parts


def run(exe, args, src, out):
    fo = "/Fo" if exe.lower().endswith("fxc.exe") else "-Fo"
    cmd = [exe] + args + [fo, out, src]
    p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, errors="replace")
    p.cmdline = cmd
    return p


def compile_all(exe, base_args, tag, strip_flag=None, echo=False):
    """Compile the corpus, returning {shader: bytes}. Raises on any failure -- a
    measurement over a file that was never written is the invalid-probe trap wearing a
    different hat."""
    out = {}
    for src in CORPUS:
        args = list(base_args) + ([strip_flag] if strip_flag else [])
        dst = os.path.join(ART, f"{os.path.splitext(src)[0]}.{tag}.cso")
        p = run(exe, args, src, dst)
        if src == CORPUS[0] and echo:
            rel = [os.path.relpath(t, HERE)
                   if os.path.isabs(t) and os.path.abspath(t).startswith(HERE + os.sep)
                   else t for t in p.cmdline]
            print(f"  $ {' '.join(rel)}   (and the same for the other two shaders)")
        if p.returncode != 0 or not os.path.isfile(dst):
            print(f"  FAILED {tag} {src}: exit={p.returncode}\n{p.stdout}\n{p.stderr}")
            return None
        with open(dst, "rb") as f:
            out[src] = f.read()
    return out


def table(title, rows, cols):
    print(f"\n{title}")
    w = [max(len(str(r[i])) for r in [cols] + rows) for i in range(len(cols))]
    print("  " + "  ".join(str(c).ljust(w[i]) for i, c in enumerate(cols)))
    print("  " + "  ".join("-" * w[i] for i in range(len(cols))))
    for r in rows:
        print("  " + "  ".join(str(c).ljust(w[i]) for i, c in enumerate(r)))


def controls():
    """The harness itself can be silently wrong. A ratio calculator that reports ~0.85 for
    every input is indistinguishable from the reported bug, so both ends of the scale are
    pinned before any compiler number is believed. Thresholds are declared in expected.md."""
    blob, h = b"", hashlib.sha256(b"dxc-2128").digest()
    while len(blob) < 4096:
        blob += h
        h = hashlib.sha256(h).digest()
    blob = blob[:4096]
    with open(os.path.join(HERE, "repro.hlsl"), "rb") as f:
        text = f.read()
    rows = [
        ["incompressible (sha256 chain, 4096 B)", len(blob), len(deflate(blob)),
         f"{ratio(blob):.3f}", ">= 0.98", "PASS" if ratio(blob) >= 0.98 else "FAIL"],
        ["compressible (repro.hlsl source)", len(text), len(deflate(text)),
         f"{ratio(text):.3f}", "<= 0.50", "PASS" if ratio(text) <= 0.50 else "FAIL"],
    ]
    table("HARNESS CONTROLS", rows,
          ["input", "bytes", "deflated", "ratio", "expect", ""])
    return all(r[-1] == "PASS" for r in rows)


def main_comparison():
    dxc, fxc = find_dxc(), find_fxc()
    print(f"dxc: {dxc}")
    print(f"fxc: {fxc}")
    for exe, flag in ((dxc, "--version"), (fxc, None)):
        if exe and flag:
            v = subprocess.run([exe, flag], capture_output=True, text=True)
            print(f"dxc --version: {v.stdout.strip()}")
    print(f"dxc args: {' '.join(DXC_ARGS)}")
    print(f"fxc args: {' '.join(FXC_ARGS)}")

    ok = controls()
    if not ok:
        print("\nHARNESS CONTROL FAILED -- no number below is usable.")
        return 1

    sets = {}
    print("\nCOMMANDS RUN")
    sets["dxc"] = compile_all(dxc, DXC_ARGS, "dxc", echo=True)
    sets["dxc+strip"] = compile_all(dxc, DXC_ARGS, "dxc-strip", STRIP, echo=True)
    if fxc:
        sets["fxc"] = compile_all(fxc, FXC_ARGS, "fxc", echo=True)
        sets["fxc+strip"] = compile_all(fxc, FXC_ARGS, "fxc-strip", "/Qstrip_reflect",
                                        echo=True)

    rows, totals = [], {}
    # corpus-large.hlsl is a 32x [unroll], so its object is 32 near-identical blocks --
    # artificially compressible for BOTH compilers and not representative of real shader
    # code. The subset total exists so the corpus bias is visible in the file rather than
    # having to be argued for in prose.
    subset = [s for s in CORPUS if s != "corpus-large.hlsl"]
    for name, blobs in sets.items():
        if not blobs:
            continue
        raw = sum(len(b) for b in blobs.values())
        zip_ = sum(len(deflate(b)) for b in blobs.values())
        sraw = sum(len(blobs[s]) for s in subset)
        szip = sum(len(deflate(blobs[s])) for s in subset)
        totals[name] = (raw, zip_, sraw, szip)
        for src in CORPUS:
            b = blobs[src]
            rows.append([src, name, len(b), len(deflate(b)), f"{ratio(b):.3f}"])
        rows.append(["TOTAL all 3", name, raw, zip_, f"{zip_ / raw:.3f}"])
        rows.append(["TOTAL excl. unrolled", name, sraw, szip, f"{szip / sraw:.3f}"])
    table("PER-SHADER OBJECT SIZE AND DEFLATE RATIO", rows,
          ["shader", "compiler", "bytes", "deflated", "ratio"])

    if "fxc" in totals and "dxc" in totals:
        rows = []
        for a, b in (("dxc", "fxc"), ("dxc+strip", "fxc+strip")):
            if a in totals and b in totals:
                rows.append([f"{a} vs {b}",
                             f"{totals[a][0] / totals[b][0]:.2f}x",
                             f"{totals[a][1] / totals[b][1]:.2f}x",
                             f"{totals[a][2] / totals[b][2]:.2f}x",
                             f"{totals[a][3] / totals[b][3]:.2f}x"])
        table("SIZE MULTIPLE OVER THE CORPUS (reporter claimed ~3x zipped)", rows,
              ["comparison", "raw all 3", "zipped all 3",
               "raw excl. unrolled", "zipped excl. unrolled"])

    for name, blobs in sets.items():
        if not blobs:
            continue
        rows = []
        for src in CORPUS:
            parts = parse_container(blobs[src])
            if parts is None:
                rows.append([src, "(not a DXBC/DXIL container)", "", "", ""])
                continue
            for cc, data in parts:
                rows.append([src, cc, len(data), len(deflate(data)),
                             f"{ratio(data):.3f}"])
        table(f"PART BREAKDOWN -- {name}", rows,
              ["shader", "part", "bytes", "deflated", "ratio"])
    return 0


def history():
    """Whole-file ratio for every cached release, oldest first. The framework's `bisect`
    cannot help here -- it scores a text predicate -- so the history search is this loop.
    Release paths come from the shared catalog via a read-only SELECT."""
    q = subprocess.run(
        [sys.executable, os.path.join(SKILL, "scripts", "triage.py"), "sql",
         "SELECT tag, build_date, cached_path FROM releases "
         "WHERE cached_path IS NOT NULL ORDER BY build_date"],
        capture_output=True, text=True)
    rels = json.loads(q.stdout)
    if not controls():
        print("\nHARNESS CONTROL FAILED -- no number below is usable.")
        return 1
    rows = []
    for r in rels + [{"tag": "main-debug", "build_date": "(ground truth)",
                      "cached_path": find_dxc()}]:
        blobs = compile_all(r["cached_path"], DXC_ARGS, "hist")
        if not blobs:
            rows.append([r["build_date"], r["tag"], "-", "-", "-"])
            continue
        raw = sum(len(b) for b in blobs.values())
        zip_ = sum(len(deflate(b)) for b in blobs.values())
        rows.append([r["build_date"], r["tag"], raw, zip_, f"{zip_ / raw:.3f}"])
    table("CORPUS TOTAL PER RELEASE (dxc, -T ps_6_0 -E main -O3)", rows,
          ["built", "tag", "bytes", "deflated", "ratio"])
    return 0


def parts_only(exe, tag):
    """Per-part breakdown for one specific compiler, kept out of the main comparison's
    artifact names so it cannot overwrite the ground-truth objects."""
    print(f"dxc: {exe}")
    v = subprocess.run([exe, "--version"], capture_output=True, text=True)
    print(f"dxc --version: {v.stdout.strip()}")
    if not controls():
        return 1
    print("\nCOMMANDS RUN")
    blobs = compile_all(exe, DXC_ARGS, tag, echo=True)
    if not blobs:
        return 1
    rows = []
    for src in CORPUS:
        for cc, data in parse_container(blobs[src]) or []:
            rows.append([src, cc, len(data), len(deflate(data)), f"{ratio(data):.3f}"])
        rows.append([src, "(whole file)", len(blobs[src]), len(deflate(blobs[src])),
                     f"{ratio(blobs[src]):.3f}"])
    table(f"PART BREAKDOWN -- {tag}", rows,
          ["shader", "part", "bytes", "deflated", "ratio"])
    return 0


if __name__ == "__main__":
    os.makedirs(ART, exist_ok=True)
    if "--parts" in sys.argv:
        i = sys.argv.index("--parts")
        sys.exit(parts_only(sys.argv[i + 1], sys.argv[i + 2]))
    sys.exit(history() if "--history" in sys.argv else main_comparison())
