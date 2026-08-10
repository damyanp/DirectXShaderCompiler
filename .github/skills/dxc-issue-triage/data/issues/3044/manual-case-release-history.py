"""Release history for issue 3044, as an explicit matrix rather than `bisect`.

`triage.py bisect` MUST NOT be used here. dxc's preprocess option changed
grammar in 8bf2b087c (PR 4624, 2022-08-31): before it, `P` is
`Separate<["-","/"],"P">` and `-P <name>` names the OUTPUT file; after it, `P`
is a `Flag` and `-Fi <name>` names the output. Releases <= v1.7.2207 therefore
answer "Unknown argument: '-Fi'", which triggers run()'s automatic spelling
re-probe -- and the `/Fi` command that re-probe builds is silently DESTRUCTIVE
on those releases, because `-P repro.hlsl /Fi preprocessed.i` makes repro.hlsl
the output file and overwrites the repro with preprocessed text, exit 0.

So each release is run here in its own scratch directory, with fresh copies of
both shaders, using the spelling that release accepts -- and the spelling that
was accepted is recorded in the output.

Per release this measures:

  repro           does the preprocessed output still contain the `keepme3044`
                  token that repro.hlsl carries ONLY inside comments?
  control         does the preprocessed output of control-token-in-code.hlsl --
                  identical except that `keepme3044` is also a code identifier
                  -- contain it? This is the positive control, run at every
                  release, so "no comments here" cannot be a dead search.
  expanded        did the macro expand? proves preprocessing actually ran.
  -C / -CC        is clang's comment-retention spelling parsed at all?
  /C /CC          the `/` spellings, compared BYTE-FOR-BYTE against a run with
                  no flag at all and against /ZZZNONSENSE, which is the control
                  for "dxc ignores unknown `/` flags silently".

Usage (from the workspace root):
    python data/issues/3044/manual-case-release-history.py > \
           data/issues/3044/manual-case-release-history.txt
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

SENTINEL = "keepme3044"
EXPANDED = "return selftest3044 + macroexpanded3044"
SHADERS = ("repro.hlsl", "control-token-in-code.hlsl")


def run(exe, work, argv):
    """Run one dxc command, echoing exactly what was executed."""
    p = subprocess.run([exe] + argv, cwd=work, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print(f"    $ dxc {subprocess.list2cmdline(argv)}")
    msg = (p.stderr or p.stdout).strip().splitlines()
    print(f"      exit={p.returncode}"
          + (f"  {msg[0][:110]}" if msg else ""))
    return p


def preprocess(exe, work, src, out, extra=()):
    """Preprocess `src` to `out`, using whichever option grammar dxc accepts.

    Returns (grammar, rc, text-or-None). Never mixes the two grammars: the mix
    is what overwrites the input file on the old one.
    """
    for grammar, argv in (
            ("new", ["-P", *extra, src, "-Fi", out]),
            ("old", ["-P", out, *extra, src]),
    ):
        if os.path.isfile(os.path.join(work, out)):
            os.remove(os.path.join(work, out))
        p = run(exe, work, argv)
        if "Unknown argument" in (p.stderr or ""):
            continue
        path = os.path.join(work, out)
        if p.returncode == 0 and os.path.isfile(path):
            with open(path, encoding="utf-8", errors="replace") as f:
                return grammar, p.returncode, f.read()
        return grammar, p.returncode, None
    return "none", p.returncode, None


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] if text \
        else "-"


def measure(tag, exe):
    work = os.path.join(HERE, f"work-{tag}")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    for s in SHADERS:
        shutil.copy(os.path.join(HERE, s), work)

    print(f"\n=== {tag}   {triage.display_exe(exe)}")
    row = {"tag": tag}

    grammar, rc, repro_i = preprocess(exe, work, "repro.hlsl", "repro.i")
    row["grammar"] = grammar
    row["repro_ok"] = repro_i is not None
    row["comments_kept"] = bool(repro_i) and SENTINEL in repro_i
    row["expanded"] = bool(repro_i) and EXPANDED in repro_i
    row["plain_sha"] = sha(repro_i)

    _g, _rc, ctrl_i = preprocess(exe, work, "control-token-in-code.hlsl",
                                 "control.i")
    row["control_ok"] = ctrl_i is not None
    row["control_sees_token"] = bool(ctrl_i) and SENTINEL in ctrl_i

    for flag in ("-C", "-CC", "/C", "/CC", "/ZZZNONSENSE"):
        out = "flag" + flag.replace("/", "s").replace("-", "d") + ".i"
        g, frc, text = preprocess(exe, work, "repro.hlsl", out, extra=(flag,))
        key = flag.lstrip("-/").lower() + ("d" if flag.startswith("-") else "s")
        row[key + "_rc"] = frc
        row[key + "_sha"] = sha(text)
        row[key + "_kept"] = bool(text) and SENTINEL in text

    shutil.rmtree(work, ignore_errors=True)
    return row


def main():
    triage.con()
    tags = [r["tag"] for r in triage.con().execute(
        "SELECT tag FROM releases WHERE prerelease = 0 AND asset_name IS NOT"
        " NULL ORDER BY build_date")]
    rows = []
    for tag in tags:
        rows.append(measure(tag, triage.ensure_release(tag)))
    rows.append(measure("main-debug", triage.resolve_compiler("main-debug")))

    print("\n\n=== summary "
          "(comments-kept is the symptom; control must be True everywhere)\n")
    head = (f"{'release':<16} {'grammar':<8} {'ppok':<5} {'expanded':<9} "
            f"{'comments-kept':<14} {'control-sees-token':<19} "
            f"{'-C':<18} {'/C == no flag':<14} {'/C == /ZZZ':<11}")
    print(head)
    print("-" * len(head))
    for r in rows:
        dashc = "rejected" if r["cd_rc"] not in (0, None) else "accepted(!)"
        same_none = r["cs_sha"] == r["plain_sha"]
        same_zzz = r["cs_sha"] == r["zzznonsenses_sha"]
        print(f"{r['tag']:<16} {r['grammar']:<8} {str(r['repro_ok']):<5} "
              f"{str(r['expanded']):<9} {str(r['comments_kept']):<14} "
              f"{str(r['control_sees_token']):<19} {dashc:<18} "
              f"{str(same_none):<14} {str(same_zzz):<11}")

    print("\nreleases measured: %d stable + main-debug" % len(tags))
    print("comments kept anywhere: %s"
          % sorted(r["tag"] for r in rows if r["comments_kept"]
                   or r["cd_kept"] or r["ccd_kept"] or r["cs_kept"]
                   or r["ccs_kept"]))
    print("control saw the token at: %d/%d builds"
          % (sum(1 for r in rows if r["control_sees_token"]), len(rows)))


if __name__ == "__main__":
    main()
