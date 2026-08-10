"""Probe Compiler Explorer directly, for issue #3883.

`triage.py godbolt` prints only the first line of each pane, which is not enough to decide
whether an extra comparison pane is worth publishing. This asks CE's compile API for the full
output of one (compiler, source, args) triple, so any claim made about a comparison rests on
a capture rather than on a summary line.

It is used here to answer two questions before touching the published link:
  * does FXC diagnose `uint index = index;` properly, where DXC fails internally?
  * and does FXC accept the initialised control -- the control SKILL.md requires before any
    cross-compiler difference is believed?

Usage (run from this directory)::

    python ce-probe.py <compiler-id> <source.hlsl> "<args>"

Read-only: it compiles, it publishes nothing.
"""

import json
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://godbolt.org/api/compiler/%s/compile"


def main() -> int:
    compiler, shader, args = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(os.path.join(HERE, shader), "r") as f:
        source = f.read()

    payload = {
        "source": source,
        "options": {
            "userArguments": args,
            "filters": {"execute": False, "commentOnly": False},
            "compilerOptions": {},
        },
        "lang": "hlsl",
        "allowStoreCodeDebug": False,
    }
    req = urllib.request.Request(
        API % compiler,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        res = json.load(r)

    print("### $ python " + subprocess.list2cmdline(sys.argv[1:] and
                                                    ["ce-probe.py"] + sys.argv[1:]))
    print("### compiler: %s" % compiler)
    print("### source:   %s" % shader)
    print("### args:     %s" % args)
    print("### exit:     %s" % res.get("code"))
    for stream in ("stdout", "stderr"):
        for line in res.get(stream) or []:
            print("[%s] %s" % (stream, line.get("text", "")))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
