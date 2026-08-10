# Method notes — from triaging #3066

Things that generalise beyond this issue. `SKILL.md` and `scripts/*.py` were not modified.

## 1. Compiler Explorer silently adds `-Zi -Qembed_debug` to every DXC pane

This is the biggest finding of the session and it affects any issue whose symptom is
*disassembly text*.

Whatever arguments are supplied — including via `--compilers "id:<args>"` — every CE DXC pane
compiles with `-Zi -Qembed_debug` appended. Verified by reading `!dx.source.args` in the pane
output:

```
!56 = !{!"-E", !"main", !"-T", !"ps_6_0", !"-Zi", !"-Qembed_debug"}
```

`triage.py`'s per-pane `# args:` header prints the args it *sent*, which is why the mismatch
is easy to miss — the header said `-T ps_6_0 -E main` while the output carried `!dbg` and
`; line:N col:M`.

Consequences:

* **CE cannot show DXC's default disassembly.** For #3066 that inverts two of the five
  findings: named handles and per-instruction source locations appear in CE that a plain
  command line does not print. A reader following only the link would conclude the opposite
  of the truth.
* `-Qstrip_debug` does **not** counter it. Tested locally: `-Zi -Qembed_debug -Qstrip_debug`
  still prints `%g_luminanceOut_UAV_structbuf` and `; line:N col:M`, because it strips the
  container's debug part, not the module's debug info. There is no known way to get a
  no-debug listing out of a CE pane.
* Anything using `-Qembed_debug` also embeds the **banner and the whole source** into
  `!dx.source.contents`. The existing rule "never put a token in the banner that you claim is
  absent" needs extending: **the shader source is in there too**, so any token in the repro —
  here the literal `0.0001` — will be found by a text search of the pane. Direct readers to
  look at a named line, not to search.

**Suggested habit:** after `triage.py godbolt`, grep the saved
`manual-case-godbolt-verify.txt` for `Qembed_debug` and for one token you claim is absent,
*before* citing the link. Two greps, and they caught a wrong link here.

## 2. A per-clause matrix is what makes a multi-clause `all_of` predicate legible

An `all_of` predicate is scored as one bit, so a `no-repro` tells you nothing about *which*
clause flipped. Scoring every clause against every capture and printing the grid turns the
predicate from an assertion into an artifact:

```
clause        repro       zi    plain   broken      1.4      1.5      1.9
root[0]           X        X        .        .        X        X        X   self-test
root[1]           X        X        .        .        X        X        X   self-test
root[2]           X        .        .        .        X        X        X   ask B
root[4]           X        .        .        .        .        X        X   ask D
```

Two things fall out that were not otherwise visible: the self-test columns prove the controls
fail for the *right* reason, and the single `.` in row `root[4]` at `v1.4.1907` located a
genuine behaviour change that the one-bit verdict had rendered as an uninteresting
"no-repro".

Worth doing whenever a predicate has more than about three clauses. The generator is
`make-evidence.py` in this issue's directory — a starting point, not shared code.

## 3. Investigate every `no-repro` release in an `all_of` bisect

Related, and stronger as a rule than as an observation. With `all_of`, a clean old release is
the *default* outcome for any reason at all — a different tool version, an unrelated
formatting change, one clause of six. It is tempting to read it as "the feature once worked".

Here `v1.4.1907` scored `no-repro`, and the honest reading was neither "the enhancement was
once implemented" nor "noise": exactly one clause differed, and it differed because the
disassembler used to print resource-derived value names without `-Zi`. That became the most
interesting paragraph of the write-up. It would have been missed entirely by trusting the
verdict bit.

Corollary: when the transition matters, **isolate it in a second single-purpose predicate and
bisect that too**. `match-resname.json` reproduced the same transition independently, which is
what turned "one clause looks odd" into a claim worth writing down.

## 4. A negative control that fails to compile can score `invalid-probe`, not `no-match`

The first `control-broken.hlsl` used an undeclared identifier, and the runner scored it
`invalid-probe` because the resulting `no matching function for call to` is on the
feature-absence marker list — the runner cannot tell that from an old compiler lacking an
intrinsic. Rewriting it as a plain syntax error (a missing semicolon) scored `no-repro`
cleanly.

**Rule of thumb:** when the point of a control is only "a failed compile emits no listing",
make it fail on *syntax*, not on semantics. Semantic errors risk colliding with the
feature-absence heuristics.

## 5. Small operational traps

* The agent `grep` tool errors on non-existent paths and can silently return nothing without a
  `glob`. `git --no-pager grep` and `Select-String` were reliable throughout.
* PowerShell quoting mangled `git log -S` with embedded escaped quotes into
  `fatal: unable to resolve revision`. Use single-quoted args or a simpler pickaxe string.
* When redacting absolute paths from a captured command line, rewrite **only** argv elements
  that are actually paths. A blanket rewrite turned `-T` into `<repo>/…/-T`.
* `dxc -dumpbin <container>` and the default `dxc <src>` stdout listing produce
  byte-identical annotation — both go through `dxcutil::Disassemble`. Capturing both is
  cheap, but it is not independent evidence, and saying so is better than implying two views
  agreed.
* An FXC contrast pane is not always available: SM 5.0 requires pixel-shader UAVs at `u1` or
  above, so any repro binding one to `u0` fails with `error X4509`. Check before designing a
  repro around an FXC comparison.

## 6. For readability/enhancement issues specifically

The useful question is rarely "does it still happen" — it is **"which of the requests are
already satisfied, and were they satisfied when the issue was filed?"** Three of the five
asks here needed that distinction, and one (`storeOutput` decoding) had *already* been
satisfied at filing time, which changes what a maintainer would do with the issue without
making the issue wrong.

Grounding each ask in the printer source rather than in output alone is what made this
checkable: an open `TODO` matching a request verbatim, a name table that exists and is used
for one table but not another, and a generated op-name table that shows a premise in the
issue was mistaken. Output observations alone could not have established any of those.
