import json, os, sys, urllib.request, datetime

D = r"data\issues\8737"
SRC = os.path.join(D, "repro-implicit-sample.hlsl")
OUT = os.path.join(D, "manual-godbolt-verification.txt")
SHORT = "https://godbolt.org/z/ea91a6vnj"
COMPILERS = ["dxc_1_7_2207", "dxc_1_10_2605_24", "dxc_trunk"]
ARGS = "-T ps_6_7 -E PSMain"

src = open(SRC, encoding="utf-8").read()
log = []
w = log.append

w("# manual measurement -- not a triage.py run; not scored by any predicate")
w("# purpose: notes.md/comment.md publish a Compiler Explorer link and claim all three panes")
w("#          compile with exit 0 and show 2dMS + `i32 undef` c2 + both textureStoreSample")
w("#          calls. This file is the backing evidence for that claim.")
w("# captured: " + datetime.datetime.now().astimezone().isoformat(timespec="seconds"))
w("# link:     " + SHORT)
w("# source:   " + SRC + "  (as recorded in godbolt-source.txt)")
w("# args:     " + ARGS)
w("")

req = urllib.request.Request(SHORT, method="GET",
                             headers={"User-Agent": "dxc-triage"})
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        w("$ GET %s  ->  HTTP %d  (shortlink resolves)" % (SHORT, r.status))
except Exception as e:
    w("$ GET %s  ->  FAILED: %r" % (SHORT, e))
w("")

for c in COMPILERS:
    body = json.dumps({
        "source": src,
        "options": {
            "userArguments": ARGS,
            "filters": {"commentOnly": False, "labels": True,
                        "directives": True, "trim": False, "intel": True,
                        "demangle": True},
            "compilerOptions": {}, "tools": [], "libraries": [],
        },
        "lang": "hlsl", "allowStoreCodeDebug": True,
    }).encode()
    r = urllib.request.Request(
        "https://godbolt.org/api/compiler/%s/compile" % c, data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "dxc-triage"})
    with urllib.request.urlopen(r, timeout=180) as resp:
        j = json.loads(resp.read().decode())

    asm = "\n".join(l.get("text", "") for l in j.get("asm", []))
    stderr = "\n".join(l.get("text", "") for l in j.get("stderr", []))
    code = j.get("code")

    w("=" * 78)
    w("pane: %s   [exit] %s" % (c, code))
    w("=" * 78)
    w("--- stderr ---")
    w(stderr if stderr.strip() else "(empty)")
    w("--- checks ---")
    checks = [
        ("resource table shows a 2dMS (non-array) UAV",
         any("2dMS" in l and "UAV" in l for l in asm.splitlines())),
        ("atomicBinOp present", "dx.op.atomicBinOp" in asm),
        ("atomicBinOp c2 is `i32 undef`",
         any("atomicBinOp" in l and "i32 undef, i32 -559038737" in l
             for l in asm.splitlines())),
        ("two textureStoreSample CALL sites (declare line excluded)",
         sum(l.strip().startswith("call void @dx.op.textureStoreSample")
             for l in asm.splitlines()) == 2),
    ]
    for name, ok in checks:
        w("  [%s] %s" % ("PASS" if ok else "FAIL", name))
    w("--- the lines those checks read ---")
    for l in asm.splitlines():
        if ("UAV" in l and "2dMS" in l) or "dx.op.atomicBinOp" in l \
           or "dx.op.textureStoreSample" in l:
            w("  " + l.strip())
    w("")

open(OUT, "w", encoding="utf-8").write("\n".join(log) + "\n")
print("\n".join(log))
