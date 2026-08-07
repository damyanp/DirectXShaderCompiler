import json, sys, urllib.request

CE = "https://godbolt.org"

def compile_on_ce(cid, args, source):
    req = urllib.request.Request(
        f"{CE}/api/compiler/{cid}/compile",
        data=json.dumps({
            "source": source,
            "options": {
                "userArguments": args,
                "filters": {"binary": False, "execute": False, "intel": True,
                            "demangle": True, "labels": True, "libraryCode": True,
                            "directives": False, "commentOnly": False,
                            "trim": False},
                "compilerOptions": {},
            },
            "lang": "hlsl",
        }).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)

def show(title, cid, args, source):
    d = compile_on_ce(cid, args, source)
    print(f"===== {title} :: {cid} :: {args}")
    print(f"exit={d.get('code')}")
    for stream in ("stdout", "stderr"):
        for line in d.get(stream) or []:
            print(f"[{stream}] {line.get('text','')}")
    asm = [ln.get("text", "") for ln in (d.get("asm") or [])]
    if asm:
        print(f"[asm] {len(asm)} lines; "
              f"'unreachable' present: {any('unreachable' in ln for ln in asm)}")
        for ln in asm:
            print(f"[asm] {ln}")
    print()

if __name__ == "__main__":
    which = sys.argv[1]
    src = open(sys.argv[2], encoding="utf-8").read()
    for spec in sys.argv[3:]:
        cid, _, args = spec.partition("|")
        show(which, cid, args, src)
