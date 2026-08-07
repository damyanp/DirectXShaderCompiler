#!/usr/bin/env python3
r"""Measure the MSF superblock of the separate PDB that dxc writes for #3005.

Why this script exists
----------------------
The triage harness scores `match.json` predicates over dxc's combined
stdout/stderr and its exit code. #3005's symptom is a property of a *file* dxc
writes -- the MSF superblock of the `-Fd` PDB -- and **no predicate kind can
inspect a file**. So the decisive measurement is made here, and its verified
output is committed as `manual-case-*.txt`.

What it measures
----------------
The MSF 7.00 superblock, which DXC declares itself in `lib/DXIL/DxilPDB.cpp`:

    0x00  char     MagicBytes[32]   "Microsoft C/C++ MSF 7.00\r\n\x1aDS\0\0\0"
    0x20  uint32le BlockSize
    0x24  uint32le FreeBlockMapBlock
    0x28  uint32le NumBlocks
    0x2C  uint32le NumDirectoryBytes
    0x30  uint32le Unknown1
    0x34  uint32le BlockMapAddr

The reported defect is that `NumBlocks * BlockSize != <size of file on disk>`.
DXC's own header comment states that invariant verbatim
(`lib/DXIL/DxilPDB.cpp`, above the `NumBlocks` field):

    "In practice, NumBlocks * BlockSize is equivalent to the size of the MSF
     file."

Two `-Fd` spellings are measured, because they are different code paths through
argument handling and produce differently sized containers:

  as-filed   `-Fd pdb\<label>\`         trailing slash: dxc auto-names by hash
  named      `-Fd pdb\<label>\repro.pdb` explicit name

Usage
-----
    python measure_msf.py --dxc <path\to\dxc.exe> [--label NAME]
    python measure_msf.py --dxc a.exe --dxc b.exe ...      # several compilers
    python measure_msf.py --from-catalog                   # every cached release
    python measure_msf.py --file some.pdb                  # just parse a file

Run it from this issue directory. Output goes under `pdb/`, which is gitignored.
Exit status is 0 whatever it finds: this is a measurement, not a test.
"""

import argparse
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUTROOT = os.path.join(HERE, "pdb")
SHADER = "repro.hlsl"

MSF_MAGIC = b"Microsoft C/C++ MSF 7.00\r\n\x1aDS\x00\x00\x00"

FIELDS = [("BlockSize", 0x20), ("FreeBlockMapBlock", 0x24), ("NumBlocks", 0x28),
          ("NumDirectoryBytes", 0x2C), ("Unknown1", 0x30), ("BlockMapAddr", 0x34)]

# The reporter's flags, verbatim apart from the paths. `-Fd` and `-Fo` are
# filled in per case.
BASE = ["-Zi", "-Qstrip_debug", "-Zsb", SHADER, "-T", "ps_6_0"]


def hexdump(b, upto=0x50):
    out = []
    for off in range(0, min(len(b), upto), 16):
        row = b[off:off + 16]
        hx = " ".join(f"{c:02x}" for c in row)
        txt = "".join(chr(c) if 32 <= c < 127 else "." for c in row)
        out.append(f"{off:08x}  {hx:<47}  |{txt}|")
    return "\n".join(out)


def parse_superblock(path):
    """Return (dict-of-fields, raw-header-bytes, filesize)."""
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        head = f.read(0x50)
    sb = {name: struct.unpack_from("<I", head, off)[0] for name, off in FIELDS}
    sb["_magic_ok"] = head[:32] == MSF_MAGIC
    return sb, head, size


def llvm_superblock_checks(sb, size):
    """Reproduce llvm::msf::validateSuperBlock + PDBFile::parseFileHeaders.

    LLVM is the de-facto specification for MSF 7.00 -- it is what llvm-pdbutil,
    lld and LLDB read PDBs with. Reproduced from
    llvm/lib/DebugInfo/MSF/MSFCommon.cpp and
    llvm/lib/DebugInfo/PDB/Native/PDBFile.cpp (llvm-project @ main).

    Deliberately faithful, including what LLVM does NOT check: it never
    compares NumBlocks * BlockSize against the file size, only that the file
    size is a whole number of blocks. That is the difference between "violates
    the documented invariant" and "a conformant reader rejects it", and it is
    the thing that decides this issue's severity.
    """
    problems = []
    if not sb["_magic_ok"]:
        problems.append("MSF magic header doesn't match")
    if sb["BlockSize"] not in (512, 1024, 2048, 4096):
        problems.append("Unsupported block size.")
    if sb["NumDirectoryBytes"] % 4:
        problems.append("Directory size is not multiple of 4.")
    ndb = -(-sb["NumDirectoryBytes"] // sb["BlockSize"]) if sb["BlockSize"] else 0
    if sb["BlockSize"] and ndb > sb["BlockSize"] // 4:
        problems.append("Too many directory blocks.")
    if sb["BlockMapAddr"] == 0:
        problems.append("Block 0 is reserved")
    if sb["BlockMapAddr"] >= sb["NumBlocks"]:
        problems.append("Block map address is invalid.")
    if sb["FreeBlockMapBlock"] not in (1, 2):
        problems.append("The free block map isn't at block 1 or block 2.")
    if sb["BlockSize"] and size % sb["BlockSize"]:
        problems.append("File size is not a multiple of block size")
    return problems


def read_u32(b, off):
    return struct.unpack_from("<I", b, off)[0]


def walk_directory(path, sb):
    """Walk the MSF stream directory and return the block indices it uses.

    Same algorithm as DXC's own reader, `PDBReader::ReadWholeStream` in
    `lib/DXIL/DxilPDB.cpp`: read `BlockMapAddr`'s block as a list of
    stream-directory block indices, then read the directory as
    `[NumStreams][size per stream][block indices per stream]`.

    The point of doing this rather than trusting the header is that it answers a
    sharper question than "does NumBlocks equal the file size in blocks": it
    says whether the file references a block the superblock declares does not
    exist. That is the difference between a cosmetic count and a structural
    inconsistency.
    """
    bs, ndb = sb["BlockSize"], sb["NumDirectoryBytes"]
    ndirblocks = -(-ndb // bs)
    with open(path, "rb") as f:
        data = f.read()

    def block(i):
        return data[i * bs:(i + 1) * bs]

    dirblocks = [read_u32(block(sb["BlockMapAddr"]), 4 * i)
                 for i in range(ndirblocks)]
    directory = b"".join(block(i) for i in dirblocks)[:ndb]
    nstreams = read_u32(directory, 0)
    sizes = [read_u32(directory, 4 * (1 + i)) for i in range(nstreams)]
    pos, streams = 1 + nstreams, []
    for s in sizes:
        n = -(-s // bs)
        streams.append([read_u32(directory, 4 * (pos + j)) for j in range(n)])
        pos += n
    used = sorted({b for blk in streams for b in blk}
                  | set(dirblocks) | {0, 1, 2, sb["BlockMapAddr"]})
    return {"num_streams": nstreams, "sizes": sizes, "streams": streams,
            "directory_blocks": dirblocks, "used_blocks": used,
            "max_block": max(used)}


def report_pdb(path, out):
    sb, head, size = parse_superblock(path)
    bs = sb["BlockSize"]
    on_disk = size // bs if bs else 0
    claimed = sb["NumBlocks"] * bs
    out(f"  file            : {os.path.basename(path)}")
    out(f"  size on disk    : {size} bytes = {on_disk} x {bs}-byte blocks"
        if bs and size % bs == 0 else
        f"  size on disk    : {size} bytes (NOT a whole number of blocks)")
    out(f"  magic           : {'ok' if sb['_magic_ok'] else 'MISMATCH'}")
    for name, off in FIELDS:
        out(f"  {name:<16}@{off:#04x}: {sb[name]}")
    out(f"  NumBlocks*BlockSize = {claimed}; file size = {size}; "
        f"difference = {(size - claimed) // bs if bs else '?'} block(s)")
    present = claimed != size
    out(f"  SYMPTOM         : {'PRESENT' if present else 'absent'} "
        f"(NumBlocks {'short by ' + str(on_disk - sb['NumBlocks']) if present else 'matches file size'})")
    d = None
    try:
        d = walk_directory(path, sb)
    except Exception as e:                                   # noqa: BLE001
        out(f"  stream directory: could not be walked: {e}")
    if d:
        out(f"  streams         : {d['num_streams']}, sizes {d['sizes']}")
        for i, blk in enumerate(d["streams"]):
            out(f"    stream {i} ({d['sizes'][i]:>5} bytes) blocks {blk}")
        out(f"  highest block index actually used : {d['max_block']}")
        out(f"  highest block index NumBlocks allows: {sb['NumBlocks'] - 1}")
        out(f"  OUT-OF-RANGE BLOCKS: "
            f"{[b for b in d['used_blocks'] if b >= sb['NumBlocks']] or 'none'}")
    probs = llvm_superblock_checks(sb, size)
    out(f"  llvm validateSuperBlock + parseFileHeaders: "
        f"{'; '.join(probs) if probs else 'no complaint'}")
    out("  first 0x50 bytes:")
    out("\n".join("    " + ln for ln in hexdump(head).splitlines()))
    return {"file": os.path.basename(path), "size": size, "blocks_on_disk": on_disk,
            "num_blocks": sb["NumBlocks"], "block_size": bs, "symptom": present,
            "llvm_problems": probs,
            "oob": [b for b in d["used_blocks"] if b >= sb["NumBlocks"]] if d else None}


def pdbutil_compare(pdbutil, src, out):
    """Dump a PDB with llvm-pdbutil as written, and again with NumBlocks fixed.

    The two files differ in exactly four bytes, so anything that differs
    between the two dumps is attributable to `NumBlocks` and nothing else.
    That is the control for the severity question: does a conformant reader
    actually care about the value, or only about the file size?
    """
    fixed = os.path.splitext(src)[0] + "-numblocks-corrected.pdb"
    with open(src, "rb") as f:
        data = bytearray(f.read())
    bs = read_u32(data, 0x20)
    real, claimed = len(data) // bs, read_u32(data, 0x28)
    struct.pack_into("<I", data, 0x28, real)
    with open(fixed, "wb") as f:
        f.write(data)
    out(f"  control: copied {os.path.basename(src)} with NumBlocks "
        f"{claimed} -> {real}; the two files differ in 4 bytes at 0x28.")
    for tag, path in (("as dxc wrote it", src), ("NumBlocks corrected", fixed)):
        for sub in (["dump", "--summary"], ["dump", "--streams", "--stream-blocks"]):
            out(f"  $ llvm-pdbutil {' '.join(sub)} {os.path.relpath(path, HERE)}"
                f"        # {tag}")
            p = subprocess.run([pdbutil] + sub + [path], capture_output=True,
                               text=True, errors="replace", timeout=300)
            out(f"  exit: {p.returncode}")
            for line in (p.stdout + p.stderr).splitlines():
                if line.strip():
                    out(f"  | {line.rstrip()}")


def dxc_version(exe):
    try:
        p = subprocess.run([exe, "--version"], capture_output=True, text=True,
                           errors="replace", timeout=120)
        return (p.stdout + p.stderr).strip().splitlines()[0]
    except Exception as e:                                   # noqa: BLE001
        return f"<version query failed: {e}>"


def run_case(exe, reldir, fd_arg, out):
    """Compile the repro into `reldir` (relative to this issue dir) and measure.

    Every path handed to dxc is relative and every path printed is relative, so
    the captured evidence is the same on any machine and can be re-run from a
    fresh clone.
    """
    absdir = os.path.join(HERE, reldir)
    os.makedirs(absdir, exist_ok=True)
    for f in os.listdir(absdir):
        os.remove(os.path.join(absdir, f))
    args = BASE + ["-Fd", fd_arg, "-Fo", os.path.join(reldir, "a.dxbc")]
    out(f"  $ dxc {' '.join(args)}")
    p = subprocess.run([exe] + args, cwd=HERE, capture_output=True, text=True,
                       errors="replace", timeout=600)
    out(f"  exit            : {p.returncode}")
    for line in (p.stdout + p.stderr).splitlines():
        out(f"  | {line}")
    pdbs = [os.path.join(absdir, f) for f in sorted(os.listdir(absdir))
            if f.lower().endswith(".pdb")]
    if not pdbs:
        out("  NO PDB PRODUCED -- this compiler is invalid evidence for #3005")
        return None
    return report_pdb(pdbs[0], out)


def catalog_compilers():
    """Read cached release paths out of the triage database. Read-only.

    A convenience for scanning history; `--dxc` is the portable path and does
    not need the database at all.
    """
    import sqlite3
    db = os.path.abspath(os.path.join(
        HERE, "..", "..", "..", ".cache", "triage.db"))
    if not os.path.isfile(db):
        sys.exit(f"no triage database at {db}; pass --dxc instead")
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    rows = c.execute("SELECT tag, cached_path, build_date FROM releases "
                     "WHERE bisectable = 1 AND cached_path IS NOT NULL "
                     "ORDER BY build_date").fetchall()
    return [(r["tag"], r["cached_path"]) for r in rows
            if os.path.exists(r["cached_path"])]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dxc", action="append", default=[],
                    help="a dxc.exe to compile the repro with (repeatable)")
    ap.add_argument("--label", action="append", default=[],
                    help="label for the matching --dxc (defaults to a counter)")
    ap.add_argument("--from-catalog", action="store_true",
                    help="also measure every release already in the triage cache")
    ap.add_argument("--file", help="skip compiling; just parse this .pdb")
    ap.add_argument("--pdbutil", metavar="EXE",
                    help="path to llvm-pdbutil.exe. Used with --file: dumps "
                         "the PDB as dxc wrote it and again with NumBlocks "
                         "corrected, isolating what the field actually costs.")
    ap.add_argument("--patch-numblocks", nargs=2, metavar=("IN", "OUT"),
                    help="write a copy of IN to OUT with NumBlocks set to the "
                         "file's real block count. A control: everything else "
                         "is byte-identical, so any behaviour that differs "
                         "between the two is attributable to this field alone.")
    a = ap.parse_args()

    lines = []

    def out(s=""):
        print(s)
        lines.append(s)

    if a.patch_numblocks:
        src, dst = a.patch_numblocks
        with open(src, "rb") as f:
            data = bytearray(f.read())
        bs = read_u32(data, 0x20)
        real = len(data) // bs
        out(f"patching {src} -> {dst}: NumBlocks {read_u32(data, 0x28)} -> {real}")
        struct.pack_into("<I", data, 0x28, real)
        with open(dst, "wb") as f:
            f.write(data)
        report_pdb(dst, out)
        return 0

    if a.file:
        report_pdb(a.file, out)
        if a.pdbutil:
            out()
            pdbutil_compare(a.pdbutil, a.file, out)
        return 0

    targets = [(a.label[i] if i < len(a.label) else f"dxc{i}", e)
               for i, e in enumerate(a.dxc)]
    if a.from_catalog:
        targets += catalog_compilers()
    if not targets:
        ap.error("nothing to measure: pass --dxc, --from-catalog or --file")

    summary = []
    for label, exe in targets:
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", label)
        out(f"=== {label} ===")
        out(f"  exe             : {exe}")
        out(f"  version         : {dxc_version(exe)}")
        for mode in ("as-filed", "named"):
            reldir = os.path.join("pdb", safe, mode)
            fd = reldir + os.sep if mode == "as-filed" \
                else os.path.join(reldir, "repro.pdb")
            out(f"  -- {mode} --")
            summary.append((label, mode, run_case(exe, reldir, fd, out)))
        out()

    out("=== summary ===")
    out(f"{'compiler':<16} {'-Fd form':<9} {'size':>7} {'blocks':>7} "
        f"{'NumBlocks':>10} {'symptom':<8} llvm reader")
    for label, mode, r in summary:
        if r is None:
            out(f"{label:<16} {mode:<9} {'-':>7} {'-':>7} {'-':>10} "
                f"{'no-pdb':<8} n/a")
            continue
        out(f"{label:<16} {mode:<9} {r['size']:>7} {r['blocks_on_disk']:>7} "
            f"{r['num_blocks']:>10} {'PRESENT' if r['symptom'] else 'absent':<8} "
            f"{'; '.join(r['llvm_problems']) or 'accepts'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
