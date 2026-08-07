# #2191 - Assert when a static const uint is used with [numthreads]

**Verdict: `repros`.** The assert still fires on a Debug build of `main`
(`1.9.0.15422 (main, eff900d54)`), unchanged, seven years after the report.

## The report

Filed 2019-05-15 by @tristanlabelle, three lines of HLSL, labelled `bug`, milestone
`Dormant`, still open. The title is the entire symptom statement - no assert message, no
stack, no build configuration. The one comment (@llvm-beanz, 2024) only re-links #2188.

## What was run

| | |
| --- | --- |
| ground truth | `main-debug` = `build/Debug/bin/dxc.exe`, `1.9.0.15422 (main, eff900d54)` (verified, `manual-case-version.txt`) |
| command | `-T cs_6_0 -E main repro.hlsl` (`cmd.txt`) |
| primary predicate | `match.json` - `internal_failure` |
| secondary predicate | `match-rejected.json` - `nonzero_exit`, see "the feature half" below |

`cs_6_0` was chosen as the oldest compute profile so no release could reject the repro on
profile grounds. Nothing in the report suggested nondeterminism, so `--repeat` was not used.

## Result on main (Debug)

`out-main-debug.txt`:

```
[exit] 3758096385          # 0xE0000001 = STATUS_LLVM_ASSERT
--- stderr ---
Internal compiler error: LLVM Assert
```

That stderr line is all dxc emits. The assert text goes to `OutputDebugString`, not stderr
(`lib/Support/assert.cpp`), so it needs a debugger. Under `cdb`
(`assert-stack.cmd` -> `manual-case-assert-stack.txt`):

```
Error: assert(MaybeODRUseExprs.empty() && "Leftover expressions for odr-use checking")
File:   tools\clang\lib\Sema\SemaDecl.cpp(11156)
Func:   clang::Sema::ActOnFinishFunctionBody

01 dxcompiler!llvm_assert+0x51
02 dxcompiler!clang::Sema::ActOnFinishFunctionBody+0x121d
04 dxcompiler!clang::Parser::ParseFunctionStatementBody+0x33b
0b dxcompiler!clang::ParseAST+0x3e7
```

Front-end only - it never reaches codegen, DXIL or validation.

## Variants, and what they pin down

| file | input | exit | reading |
| --- | --- | --- | --- |
| `variant-literal-main-debug.txt` | `[numthreads(8, 8, 1)]`, `static const` left in place but unused | 0 | negative control: the predicate does not fire on a known-good input, and the `static const` *declaration* is not the trigger - the *reference from the attribute* is |
| `variant-odr-used-main-debug.txt` | `[numthreads(eight, 8, 1)]` **and** `buf[0] = eight;` in the body | 0 | the empty body is load-bearing. Any full expression in the body drains the bookkeeping the assert checks, and the assert stops firing. Doubles as a user workaround |
| `variant-maxvertexcount-main-debug.txt` | `[maxvertexcount(three)]` on an empty-bodied GS, `-T gs_6_0` | 0xE0000001 | **same assert, different attribute.** The title understates the scope |

The `[maxvertexcount]` variant is worth a warning to whoever re-runs this. The first version
of it had a body (`o.pos = v[0]; s.Append(o);`) and compiled cleanly - which would have
supported the false conclusion that the defect is `[numthreads]`-specific. The confound is
exactly what `variant-odr-used` isolates. `--expect match` caught it loudly:

```
WARNING: control expected match but scored no-repro. Either the predicate does not
discriminate, or the control is not what you think it is.
```

Both attributes share `ValidateAttributeIntArg` (`SemaHLSL.cpp:13858`), whose
identifier-argument branch looks the `VarDecl` up and constant-folds its initialiser. 28
attributes route through it (counted in `manual-case-source-evidence.txt`), including
`[maxvertexcount]`, `[instance]`, `[outputcontrolpoints]`, the work-graph node attributes,
and most of the `[[vk::...]]` family.

## History: the release axis cannot answer this question

`bisect --linear` over all 20 catalogued releases, v1.4.1907 (2019-07) to v1.9.2607:
**every one exits 0**, and every one emits the right thread-group size,
`!{i32 8, i32 8, i32 1}` (the `; NumThreads=(8,8,1)` comment line only appears from
v1.7.2207 onward; older releases did not print it).

That is **not** evidence of a fix, and recording it as `never-repro'd-in-releases` without
saying so would be a wrong verdict. Every release binary is a **Release** build, and
`include/llvm/llvm_assert/assert.h` makes `assert` a no-op under `NDEBUG`. The symptom is
structurally unobservable in all 20 probes. They are valid probes - they compile the repro,
so `invalid-probe` detection does not and should not flag them - of a symptom that cannot
appear in them. See `method-notes.md`.

What the release scan *does* establish is that the leftover bookkeeping is harmless to
codegen: with the assert compiled out, every release produces correct DXIL.

The `history` field is therefore recorded as `never-repro'd-in-releases` **with that
qualification inline**, so the database row cannot be misread as "fixed".

The 20 archived probes now carry `# match: match-rejected.json`, because a later run of the
secondary predicate overwrote the primary predicate's recorded scoring (same output path;
`method-notes.md` finding 3). The *measurements* survived - raw output, `# exit:`,
`# timed_out:` - so the primary-predicate claim was re-derived from them rather than trusted:
`recheck-primary-predicate.py` feeds each archived file to `triage.is_internal_failure`
(imported from the tool, not reimplemented) and reports **0 of 20**, exercising both the
exit-code branch and the output-text branch. Capture:
`manual-case-primary-predicate-recheck.txt`. Every claim in this section is therefore checkable
by a stranger from the files in this directory, with no compiler re-run.

Age, from source (`manual-case-source-evidence.txt`): both the assert and
`ValidateAttributeIntArg`'s identifier branch are unchanged since the repository's first
public commit, 2016-12-28 - 2.4 years before the report. That shows the code was never
revised. It is not proof the assert fired in 2019, and no older Debug build was tested:
rebuilding the compiler is out of scope for this triage. The honest statement is "still
asserts today, on the only Debug build measured".

## The feature half is a separate, and stale, question

#2188 and #4032 are about DXC *rejecting* a `static const` in `[numthreads]`. #4032's
reporter wrote in 2021-10 that the "compiler emits error message and rejects input", and
@pow2clk closed it here calling acceptance "a new language feature", suggesting `#define`.

That does not reproduce. `match-rejected.json` (`nonzero_exit`) was run linearly over all
20 releases specifically to rule out a mid-range rejection window that a short-circuiting
binary search would miss: **no release rejects it**, back to v1.4.1907. DXC has accepted a
`static const uint` as a `[numthreads]` argument for as long as is checkable.

This does not settle #2188, which uses a different construct (`static const uint2` plus
`.x`/`.y` member access, and the product as an array bound). That was not tested here.

## Compiler Explorer

https://godbolt.org/z/dGK17oobT - verified (HTTP 200; three panes, all `-T cs_6_0 -E main`).

CE has no assertions-enabled DXC, so the link cannot show the symptom; `godbolt-note.txt`
says so at the top of the pasted source. It is there for two things, both captured in
`manual-case-compiler-explorer.txt`:

- `dxc_1_6_2112` and `dxc_trunk` both exit 0 with `!{i32 8, i32 8, i32 1}` - shipping DXC
  resolves the `static const` correctly, so shader authors are unaffected;
- `hlsl_clang_assertions_trunk`, an **assertions** build of the successor HLSL front end,
  also exits 0 and emits metadata identical to the literal control. Controlled against
  `[numthreads(8, 8, 1)]` on the same pane, per the rule that a cross-compiler result needs
  a control before it is believed.

## Assessment

A live, reproducible, front-end assert with a three-line repro, broader than its title, and
harmless to anyone using a shipped compiler. It bites DXC developers and anyone running an
assert-enabled build - which is why it has survived seven years without a user complaint
loud enough to move it out of `Dormant`.

- **status** `repros`
- **repro quality** `complete`
- **confidence** `high` on the symptom and on its scope; the *age* claim is bounded by not
  having built an older Debug compiler
- **suggested action** `still-valid-keep-open`
- **labels** add `crash` ("DXC crashing or hitting an assert"); nothing to remove

`check-in-clang` was considered and deliberately not proposed: it asks a question this
triage already answered on `hlsl_clang_assertions_trunk`. No effort or root-cause label
(`low-hanging-fruit`, `rca`) is proposed - the write-up reports where the assert fires and
what suppresses it, and stops short of prescribing a fix.

## What was not determined

- Whether the assert fired on the 2019 compiler. Only `main` at `eff900d54` was measured in
  Debug.
- Whether the other 26 attributes routed through `ValidateAttributeIntArg` behave the same.
  Two of the 28 were tested.
- Anything about #2188's `uint2` member-access construct, or about #3092's SPIR-V
  specialisation-constant request. Both are cross-referenced from this issue and neither
  was in scope.

## Evidence index

Every measurement quoted in this file and in `comment.md` has a captured file behind it:

| claim | file |
| --- | --- |
| compiler identity `1.9.0.15422 (main, eff900d54)` | `manual-case-version.txt` (verbatim `--version`, plus binary hash) |
| repro asserts, exit `0xE0000001` | `out-main-debug.txt` |
| assert text, source line, stack | `manual-case-assert-stack.txt` (re-runnable: `assert-stack.cmd`) |
| `[maxvertexcount]` asserts too | `variant-maxvertexcount-main-debug.txt` + `manual-case-assert-stack.txt` |
| referencing the constant in the body compiles clean | `variant-odr-used-main-debug.txt` |
| literal `[numthreads(8,8,1)]` control is clean | `variant-literal-main-debug.txt` |
| all 20 releases exit 0 and emit `!{i32 8, i32 8, i32 1}` | `out-v1.4.1907.txt` ... `out-v1.9.2607.txt` |
| 28 attributes share the path; `NDEBUG`; unchanged since 2016 | `manual-case-source-evidence.txt` |
| Compiler Explorer results, with control | `manual-case-compiler-explorer.txt`, `godbolt-note.txt` |

The `manual-case-*.txt` files are hand-driven captures, not probes; each says so in its header
and none is scored by `match.json`.

Note on the release probes: the 20 `out-v*.txt` files carry `# match: match-rejected.json`,
because the second (rejection) predicate was run over the same releases and the output path
does not include the predicate name, so it overwrote the first pass - see `method-notes.md`
finding 3.

**The primary-predicate claim is still checkable, and I re-checked it rather than arguing it.**
`recheck-primary-predicate.py` re-reads all 20 archived files, takes the `# exit:` and
`# timed_out:` headers and the full archived stdout+stderr, and feeds them to
`triage.is_internal_failure` *imported from `triage.py`* - the same function `match.json` uses,
not a reimplementation. Result, captured in `manual-case-primary-predicate-recheck.txt`:

```
RESULT: 0 of 20 releases score as internal_failure.
```

So "no shipped release exhibits this internal failure" rests on the archived measurements, not
on a scoring that was overwritten.

I had first justified this by arguing that `internal_failure` is a strict subset of
`nonzero_exit`, so exit 0 would settle it. **That argument is wrong**, and it is worth recording
why: `is_internal_failure` (`triage.py:268`) ends with

```python
return re.search(INTERNAL_MARKERS, text) is not None
```

which is reached *regardless of exit code*. A compiler that exited 0 while printing
`Stack dump` or `Assertion failed` would be an internal failure and not a nonzero exit. The
two predicates are therefore not nested, and only the text branch coming back clean too - which
the re-check above actually exercises on the archived output - closes the claim.
