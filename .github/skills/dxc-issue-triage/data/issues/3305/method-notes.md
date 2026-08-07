# Method observations from triaging #3305

Recorded here rather than in `SKILL.md` / `scripts/`, per the single-writer rule. Collation
decides what to promote.

## 1. `ce_args` reads only the first `cmd.txt` line, which is exactly wrong for a
##    two-backend issue

`godbolt` prints `warning: multi-invocation cmd.txt; linking the first only` and builds every
pane's default arguments from line 1. For this issue the *whole finding* is the difference
between line 1 and line 2, so the default link would have shown the DXIL half twice. It worked
out — `--compilers "dxc_trunk,dxc_trunk:<line 2 args>"` produces exactly the right two-pane
link — but the override had to be written by hand from a file the tool had already read.

Possible promotion: when `cmd.txt` has N invocations, offer one pane per invocation by default
(`dxc_trunk` per line), or at least print the other lines' CE-form arguments so the operator can
paste them. #8732 hit an adjacent version of this (`ce_args` handing CE a second input file).

## 2. `run --shader X --label Y --expect` across releases can be *right* to violate its
##    expectation — the violation is the measurement

`variant-noparam-v1.7.2212.txt` was declared `--expect no-match` on the reasoning that a
genuinely-missing payload parameter produces a different diagnostic from the empty-payload one.
That is true on `main` and false before PR #5131 (2023-04), where both inputs produce the same
message. The `WARNING: control expected no-match but scored repro` is what surfaced the date of
the change, and `triage.py expect --expect match` was the right response, not a re-run.

This is a *third* shape of control beyond SKILL.md's negative/identity pair: a control whose
expected result is **release-dependent**. Nothing in the tooling can express "no-match from
v1.7.2308 onward, match before it", so the declaration has to be pinned per capture — which the
per-capture `# expect:` line does support, but only because the filename carries the compiler.
Worth a sentence in step 4 or step 7: when running the *same* control against several releases,
expect the declarations to differ, and treat a violated one as a date to investigate.

## 3. PowerShell truncated a native argument at the first `.`

```
& $exe -T lib_6_3 -spirv -fspv-target-env=vulkan1.2 repro.hlsl
  -> error: unknown SPIR-V target environment 'vulkan1'
& $exe -T lib_6_3 -spirv '-fspv-target-env=vulkan1.2' repro.hlsl
  -> compiles
```

Same shell, same binary, one pair of quotes apart. SKILL.md warns that PowerShell eats `$` and
backticks out of *prose*; this is the same class landing on an **argument**, and the failure
mode is worse than corrupted text, because `unknown SPIR-V target environment` reads exactly
like a genuine feature-absence result and would have been recorded as one. It cost a wrong
provisional conclusion ("v1.5.2010 cannot express any target environment") that only unravelled
on a re-run.

`triage.py` itself is immune — it `shlex.split`s `cmd.txt` and calls `subprocess.run` with a
list — so this only bites hand-run exploration, which is precisely where the tooling's guard
rails are absent. Suggested promotion: extend the existing PowerShell warning in step 5 from
prose to arguments, with this example, and say the fix is to single-quote **every** argument
containing `=` or `.`, not just those containing `$`.

## 4. A capture with two invocations pays off, and the header format already supports it

`out-*.txt` keeps a `$ dxc <line>` / `[exit]` block per invocation, so the DXIL error and the
SPIR-V module sit in one file and the disagreement is one file to read rather than two to
compare — and `bisect --linear` then gives *both* backends' history for the price of one scan
(19 of 20 releases compile the SPIR-V half; only v1.4.1907 lacks SPIR-V codegen).

The one thing it needs is that the predicate be positive and specific to one invocation's
output. An absence clause, or a clause about the "other" invocation, would have made every
pre-SPIR-V release an `invalid-probe` and thrown away a valid DXIL result. That reasoning is in
`match.json`'s note; it generalises to any multi-invocation `cmd.txt` and might belong in
step 4.

## 5. Possibly related issues (not claimed in the draft, per the brief)

Nothing found that overlaps this one. For collation's cross-issue pass, the searchable shape
here is "DXC emits an error, but the error describes a different input" — a diagnostic-quality
defect hiding inside a correctness-looking report. If other issues in this or earlier batches
resolved to that shape, `diagnostic` may be systematically under-applied in the backlog.
