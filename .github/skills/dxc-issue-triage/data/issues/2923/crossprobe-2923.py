"""Cross-probe: is the v1.6.2104 -> v1.6.2106 transition in dxc or in the pass?

manual-case-history.txt shows repro.hlsl going from `no-match` at v1.6.2104 to
`match` at v1.6.2106. Two things could have changed:

  * what dxc emits into the ILDB debug module (llvm.dbg.value coverage for the
    caller's `p`), or
  * what the PIX passes -dxil-dbg-value-to-dbg-declare /
    -dxil-annotate-with-virtual-regs do with it.

run-2923.cmd already separates the two, because PIX_DXC chooses the compiler
and PIX_DLL chooses the DLL the passes come out of. Running all four
combinations says which side moved. Writes manual-case-crossprobe.txt.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import triage  # noqa: E402

DRIVER = os.path.join(HERE, "run-2923.cmd")
TAGS = ["v1.6.2104", "v1.6.2106"]


def bins(tag):
    exe = os.path.abspath(triage.ensure_release(tag))
    return exe, os.path.join(os.path.dirname(exe), "dxcompiler.dll")


def main():
    log, rows = [], []
    for ctag in TAGS:
        cdxc, _ = bins(ctag)
        for ptag in TAGS:
            _, pdll = bins(ptag)
            env = dict(os.environ)
            env["PIX_DXC"] = cdxc
            env["PIX_DLL"] = pdll
            p = subprocess.run([DRIVER, "repro.hlsl", "-Od"], cwd=HERE,
                               env=env, capture_output=True, text=True)
            out = (p.stdout or "") + (p.stderr or "")
            v = ("match" if "PIX-2923: DECLARED-BUT-UNWRITTEN" in out
                 else "no-match" if "PIX-2923: ALL-DECLARED-REGISTERS-WRITTEN"
                 in out else f"unknown(rc={p.returncode})")
            rows.append((ctag, ptag, v))
            log.append(f"### dxc={ctag}  passes={ptag}  repro.hlsl -Od\n"
                       f"# PIX_DXC={cdxc}\n# PIX_DLL={pdll}\n"
                       f"$ run-2923.cmd repro.hlsl -Od\n{out.rstrip()}\n"
                       f"# exit: {p.returncode}   predicate: {v}\n")
            print(f"dxc={ctag:<12} passes={ptag:<12} -> {v}")

    with open(os.path.join(HERE, "manual-case-crossprobe.txt"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write("# issue: 2923\n")
        f.write("# what: which side of the v1.6.2104 -> v1.6.2106 transition\n"
                "#       moved -- the compiler that emits the debug module, or\n"
                "#       the dxcompiler.dll the PIX passes are run from.\n")
        f.write("# produced by: crossprobe-2923.py\n#\n# summary\n")
        f.write(f"# {'dxc':<14}{'PIX passes':<14}predicate\n")
        for c, pt, v in rows:
            f.write(f"# {c:<14}{pt:<14}{v}\n")
        f.write("\n" + "\n".join(log))
    print("\nwrote manual-case-crossprobe.txt")


if __name__ == "__main__":
    main()
