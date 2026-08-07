import json, os, urllib.request, datetime

D = r"data\issues\8737"
SRC = os.path.join(D, "repro-implicit-sample.hlsl")
OUT = os.path.join(D, "manual-godbolt-rejected-panes.txt")

# Each entry: (compiler id, user arguments, why notes.md says the pane was not used)
PROBES = [
    ("hlsl_clang_trunk", "-T ps_6_7 -E PSMain",
     "notes.md: no Clang pane -- RWTexture2DMS does not exist in the new front end"),
    ("rga290_dxctrunk", "-T ps_6_7 -E PSMain",
     "notes.md: no RGA pane -- CE's RGA compiles for Vulkan, not DX12"),
    ("rga290_dxctrunk", "-T ps_6_7 -E PSMain -s dx12",
     "notes.md: -s dx12 is forwarded to dxc and rejected"),
    ("rga290_dxctrunk", "-T ps_6_7 -E PSMain --dx12",
     "notes.md: --dx12 is forwarded to dxc and rejected"),
]

src = open(SRC, encoding="utf-8").read()
log = []
w = log.append
w("# manual measurement -- not a triage.py run; not scored by any predicate")
w("# purpose: notes.md explains why the Compiler Explorer link carries no Clang pane and no")
w("#          RGA pane, quoting diagnostics from both. Those were hand-observed. This file")
w("#          re-runs each probe so the negative decisions are backed by evidence too.")
w("# captured: " + datetime.datetime.now().astimezone().isoformat(timespec="seconds"))
w("# source:   " + SRC)
w("")

for cid, args, why in PROBES:
    body = json.dumps({
        "source": src,
        "options": {"userArguments": args,
                    "filters": {"commentOnly": False, "labels": True,
                                "directives": True, "trim": False,
                                "intel": True, "demangle": True},
                    "compilerOptions": {}, "tools": [], "libraries": []},
        "lang": "hlsl", "allowStoreCodeDebug": True,
    }).encode()
    r = urllib.request.Request(
        "https://godbolt.org/api/compiler/%s/compile" % cid, data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "dxc-triage"})
    try:
        with urllib.request.urlopen(r, timeout=180) as resp:
            j = json.loads(resp.read().decode())
        code = j.get("code")
        stderr = "\n".join(l.get("text", "") for l in j.get("stderr", []))
        stdout = "\n".join(l.get("text", "") for l in j.get("stdout", []))
    except Exception as e:
        code, stderr, stdout = "REQUEST FAILED", repr(e), ""

    w("=" * 78)
    w("compiler: %s" % cid)
    w("args:     %s" % args)
    w("why:      %s" % why)
    w("[exit] %s" % code)
    w("=" * 78)
    w("--- stderr ---")
    w(stderr.strip() if stderr.strip() else "(empty)")
    if stdout.strip():
        w("--- stdout ---")
        w(stdout.strip())
    w("")

open(OUT, "w", encoding="utf-8").write("\n".join(log) + "\n")
print("\n".join(log))
