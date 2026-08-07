# Method notes — from triaging 3811

Issue 3811's symptom is *partly an absence* ("produces undef with **no error/warning**"), which
is the case SKILL.md warns is easiest to get wrong. These are the concrete things that worked or
bit, written for promotion into SKILL.md.

## 1. Anchor an absence predicate on something only a successful compile can emit

The trap SKILL.md names is that a release which *fails to parse* the shader also emits no
warning, so a naive "no `warning:` in the output" predicate scores every broken release as a
textbook repro.

The fix that made it a non-issue here: **make the positive clause the load-bearing one, and pick
a positive that only successful codegen can produce.** `match.json` is

```
all_of[ regex "=\s*phi\s+float\s+\[[^\r\n]*\bundef\b", not_regex "(?i)\berror:" ]
```

A compiler that failed to parse the shader emits no DXIL, so it cannot satisfy the phi clause,
so it cannot score `repro` no matter how silent it is. Across 40 release probes (20 releases ×
2 predicates) **zero** came back `invalid-probe` — not because the runner's guard never had to
work, but because the predicate never gave it the chance.

Generalised: for a "no diagnostic is emitted" symptom, do not write `not_regex "warning:"` alone.
Pair it with a positive assertion about the *artefact the buggy compile produces*. If the symptom
has no positive artefact at all, that is a signal that the predicate needs `--expect` controls on
a known-broken input before it can be trusted.

## 2. Add `not_regex "error:"` even when the symptom is silence

Non-obvious and it nearly bit here. The DXIL validator **echoes the rejected instruction into
its own diagnostic**:

```
note: at '%4 = fadd fast float %3, undef' in block '#0' of function 'main'.
```

A rejected module's *error text* can therefore contain the very IR the predicate is looking for.
This is the same shape as the #3092 trap. The `not_regex error:` clause is doing double duty: it
states "the module was accepted" (which is half the claim) and it stops the diagnostic text from
being mistaken for emitted DXIL. Worth stating as a rule: **when a predicate matches IR text,
also assert the compile succeeded**, because validators quote IR at you.

## 3. Split a two-part symptom into two predicates *before* running, not after

The report claimed (i) undef in the DXIL and (ii) no error and no warning. Those two halves have
**diverged**: the undef is untouched on all 20 probeable releases, while the silence ended at
v1.7.2308. A single predicate would have produced a confidently wrong verdict in either
direction — `always-repro'd` (hiding that the reported wording is now false) or
`fixed-in v1.7.2308` (declaring a completely live defect fixed).

Two predicates cost one extra `bisect --linear` and gave two clean, separately-dated histories.
`probe_path()` already keeps them apart (`out-<compiler>--match-silent.txt`), so there is no
bookkeeping burden. **Heuristic: if the issue title contains "and" or a comma joining an observed
output to an observed silence, that is two predicates.**

## 4. `undef`-in-DXIL predicates do not transfer between issues

Matching `undef` anywhere in DXIL matches *correct* shaders. Two live false-positive sources
were present in this very issue:

- `dx.op.loadInput`'s trailing `gsVertexAxis` operand is `undef` in every non-GS shader — it is
  in the reporter's own 2021 paste.
- the compute restating's `dx.op.bufferStore` carries three more `float undef` operands for the
  unused components.

And the narrowing used by a *previous* issue did not work here: #3009's "undef reaching an
arithmetic **dx.op**" form fails, because the arithmetic in this repro is a plain LLVM `fadd`,
not a `dx.op` call. **Re-derive the narrowing from the actual output each time**; record the
control in the predicate's `note` (`control-initialized.hlsl` differs by one line, `result =
0.0;`, and emits `phi float [ %10, %5 ], [ 0.000000e+00, %4 ]` — same phi, constant instead of
undef, so `--expect no-match` proves the predicate reads the operand and not the opcode).

## 5. A missing-diagnostic issue needs a control in *both* directions

Not one control, two, and they prove different things:

- `variant-straightline.hlsl` (`--expect no-match`) — the check exists and the pipeline reaches
  it. Without this, "no diagnostic" could just mean the compiler never got that far.
- `control-initialized.hlsl` (`--expect no-match`) — the predicate is not firing on everything.

If either is missing, "no diagnostic was emitted" is not yet evidence. Here the first control was
also the reporter's own control, which is why the report was worth taking seriously at all.

## 6. `repro.hlsl` must be the issue body **verbatim**, with no added header

This cost a full re-capture. I had prefixed `repro.hlsl` and `variant-straightline.hlsl` with a
2-line provenance comment. Harmless — until the draft comment quoted `repro.hlsl:9:3`, which is
a line number **that exists in no file the reporter has**. Their `source.hlsl` puts it at 7:3.

The house convention (checked in issues 3009, 1877, 2792, 3055) is that `repro.hlsl` carries no
header, so every quoted `file:line` in the write-up is directly comparable to what the reporter
sees. Extracting it programmatically out of `issue.json` rather than retyping it also guarantees
tabs and comments survive:

```python
b = json.load(open("issue.json", encoding="utf-8"))["body"].replace("\r\n", "\n")
start = b.index("```\nStructuredBuffer") + 4
src = b[start : b.index("\n```", start)] + "\n"
```

Headers on *variants* are fine and useful — nobody quotes their line numbers. The rule is
narrower than "no headers": **no header on any file whose `file:line` you intend to quote.**

## 7. Validate every absence-check regex against a known positive *first*

The absolute-path audit returned "0 files" on the first run — and so did the known-positive
probe, silently, because `Select-String -Pattern "[A-Za-z]:\\\\prj"` (double-escaped, C-style)
matches nothing in PowerShell. The correct form is single-escaped:
`"[A-Za-z]:\\(prj|Users|Program)"`. Had I trusted the first clean result I would have shipped an
unverified claim.

This generalises past PowerShell: **a zero result from an unvalidated pattern is not evidence of
absence, it is evidence of nothing.** Cheapest possible guard is to run the pattern against a
string you have deliberately constructed to match, in the same shell, in the same call.

(The agent `grep` tool's silent false-zero without a `glob` filter is the same failure mode with
a different cause; `git grep` and `Select-String` were used for every load-bearing zero here.)

## 8. Prove "identical to the reported output" instead of asserting it

The strongest single line in the write-up is that today's `define void @main()` is line-for-line
identical to the DXIL pasted in 2021. Asserting that from eyeballing two 27-line blocks is
exactly the kind of claim that is wrong 5% of the time and unfalsifiable afterwards.
`compare-dxil.py` (committed, ~30 lines) extracts the block from `issue.json` and from
`out-main-debug.txt` and diffs them, writing `manual-case-dxil-identity.txt` with both line
counts and the diff. It is re-runnable by a stranger and it caught nothing — which is the point:
now it is a measurement.

Same pattern for the Compiler Explorer Clang claim: `ce-clang-control.py` counts diagnostics and
undef-seeded phis across three cases and commits the extracted IR alongside the counts, so a
reader can check the counts rather than trust them.

## 9. Cross-compiler *silence* needs controls as much as a cross-compiler *error* does

"Clang doesn't warn either" is a claim about an absence and is satisfied by a Clang pane that
failed for an unrelated reason. Three cases were needed: the loop repro, the straight-line case
(which DXC rejects — Clang emits **0** uninit diagnostics there too, so the honest finding is
"no equivalent of `-Wparameter-usage` at all", not "misses the loop case"), and the initialized
control (0 undef phis, proving the phi count really does move).

**Stage limit worth stating explicitly in the write-up:** CE's Clang pane emits pre-DXIL LLVM IR
and does **not** run the DXIL validator. So it is evidence about front-end silence only, and says
nothing about how Clang would validate. Also: Clang's DXIL backend cannot lower vertex signature
I/O, so a compute restating was required — and it was verified to still reproduce locally before
being adopted, since a restating that stops reproducing is worse than no link at all.

## 10. Corroborating from source changed the verdict, not just the prose

Reading `lib/DxilValidation/DxilValidation.cpp` turned "DXC doesn't diagnose this" into "the rule
is `bool LegalUndef = isa<PHINode>(&I);` — purely local and syntactic, PHI nodes exempt by name",
which (a) confirmed the reporter's own hypothesis verbatim, (b) settled that this is a
**validator** rule and not Sema — which is what makes the existing `validation` label correct
rather than a mislabel, and (c) explained the -Od result in advance. `git log --follow -S` on the
exempting expression dated it to the repository's first commit, which predicted the
`always-repro'd` history before the scan confirmed it.

Cheap and high-yield: **before running the release scan, find the code and date the line.** If
the source says "since 2016", a scan that says "fixed in 2023" is telling you your predicate
moved, not the behaviour.

## Small tooling gotchas

- `triage.py sql` — the compilers column is `exe_path`, not `exe`.
- `triage.py run --args` replaces the **entire** command line including the filename and bypasses
  `cmd.txt`; correct for `-Od` and for the compute variant, wrong if you expect it to append.
- PowerShell has no heredoc. `@'` … `'@ | python -` works and preserves the script exactly.
- Python: `f(*[a] or [b])` is a `SyntaxError`; it needs `f(*([a] or [b]))`.
- Capture headers already redact to `<repo>/…` and `<cache>/…`, which is why the absolute-path
  audit is clean — but the audit still has to be run, because *hand-written* files and generator
  scripts are not redacted by anything.
