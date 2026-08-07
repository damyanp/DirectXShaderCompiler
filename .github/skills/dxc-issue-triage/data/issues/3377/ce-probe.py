"""Probe Compiler Explorer directly, for issue #3377.

`triage.py godbolt` publishes and reports the FIRST line of each pane, which is not enough to
judge whether an extra comparison pane is worth adding (SKILL.md: "godbolt records only the
first line of each pane's output ... Open the link"). This asks CE's compile API for the full
output so the decision, and any claim made about it, rests on a capture.

Usage (run from this directory)::

    python ce-probe.py <compiler-id> <source.hlsl> "<args>"

Read-only: it compiles, it publishes nothing.
"""

import json
import os
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

    print("### compiler: %s" % compiler)
    print("### source:   %s" % shader)
    print("### args:     %s" % args)
    print("### exit:     %s" % res.get("code"))
    for stream in ("stdout", "stderr"):
        for line in res.get(stream) or []:
            print("[%s] %s" % (stream, line.get("text", "")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
