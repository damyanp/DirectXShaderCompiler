"""Generate control-physical400.hlsl for issue 4615.

The primary predicate contains `not_regex !DILocation\\(line: 40[01],`. A
not_regex clause that can never fail is indistinguishable from a dead regex, so
this control puts the `return` statement at *physical* line 400 with no `#line`
directive anywhere. Ground truth must then emit `!DILocation(line: 400, ...)`
and the clause must fail, i.e. the control scores `no-match`.

Lines 1-7 are byte-identical to repro.hlsl so the self-test clause
(`!DILocation(line: 7,`) still passes and a reader can see which clause moved.

Run:  python gen-control-physical400.py
"""
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "control-physical400.hlsl")

with open(os.path.join(HERE, "repro.hlsl"), encoding="utf-8") as f:
    repro = f.read().splitlines()

# repro.hlsl lines 1-7 verbatim; line 8 is the `#line` directive, which this
# control must NOT have; the `return` has to land on physical line 400.
head = repro[:7]
assert head[6].strip().startswith("float4 before ="), head[6]
body = "  return before * 2.0f;"
pad = ["" for _ in range(400 - len(head) - 1)]
lines = head + pad + [body, "}"]
assert lines[399] == body, f"return landed on physical line {lines.index(body) + 1}"

with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(lines) + "\n")

print(subprocess.list2cmdline(["python", os.path.basename(__file__)]))
print(f"wrote {os.path.basename(OUT)}: {len(lines)} lines, "
      f"`{body.strip()}` on physical line {lines.index(body) + 1}")
