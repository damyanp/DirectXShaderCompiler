# #2188 — notes

**Issue:** [fxc.exe vs dxc.exe: "static const int" use as compile time constant](https://github.com/microsoft/DirectXShaderCompiler/issues/2188)
Filed 2019-05-14, open, `bug` + `fxc-disagrees`, milestone **Dormant**, unassigned since
2024-06-18. One comment, from @tristanlabelle (2019-05-16): "I was able to repro. If this
blocking, you can use a `#define` as a workaround."

**Ground truth:** `build/Debug/bin/dxc.exe`, id `main-debug`.
`dxcompiler.dll: 1.10(5422-eff900d5)(1.9.0.15422) - 1.9.0.15422 (main, eff900d54)` —
matches the commit the build was made from, checked before any probe was run.

**Verdict:** `repros`, always, unchanged since the oldest checkable release.

---

## The repro

The issue body elides the entry point (`void csMain() ....`), so `repro.hlsl` keeps the
four declarations verbatim and completes the body. `control-inlined.hlsl` is the
reporter's own "note" version — numeric constants inlined — with a **byte-identical
body**, so the two files differ only in the thing under test. Repro quality: **partial**.

`cmd.txt`: `-T cs_6_0 -E csMain repro.hlsl`. `cs_6_0` is the oldest compute profile DXC
ships, so no release can reject the repro for predating the profile — the `invalid-probe`
trap that has faked regressions elsewhere cannot fire here, and did not (every probe below
emitted the issue's own diagnostics, not a profile or feature rejection).

## What main-debug does

`out-main-debug.txt`, exit `2147500037` = **0x80004005 (E_FAIL)**. That is dxc's ordinary
diagnosed-error status, **not** an internal failure — worth stating explicitly because the
cross-referenced #2191 describes the neighbouring case as an *assert*, and this is an
assert-enabled Debug build. Nothing asserted.

```
repro.hlsl:10:27: error: variable length arrays are not supported in HLSL
groupshared float4      S1[cThread];
                          ^
repro.hlsl:12:2: error: 'numthreads' attribute requires an integer constant
[numthreads(c2Thread.x, c2Thread.y, 1)]
 ^          ~~~~~~~~~~
repro.hlsl:12:2: error: 'numthreads' attribute requires an integer constant
[numthreads(c2Thread.x, c2Thread.y, 1)]
 ^                      ~~~~~~~~~~
repro.hlsl:12:2: warning: Group size of 0 (0 * 0 * 1) is outside of valid range [1..1024] - attribute will be ignored [-Wignored-attributes]
repro.hlsl:13:6: error: compute entry point must have a valid numthreads attribute
```

The control compiles to DXIL, exit 0, `NumThreads=(8,8,1)`,
`[256 x float]` groupshared allocation (`variant-control-inlined-main-debug.txt`).

## Isolating the cause

Each variant is the repro with exactly one thing changed; all are captured and carry a
declared `--expect` that the completeness audit re-checks at collation.

| variant | construct | exit | scored | what it shows |
| --- | --- | --- | --- | --- |
| `control-inlined` | `S1[64]`, `[numthreads(8,8,1)]` | 0 | no-repro | reporter's control holds |
| `array-only` | `S1[cThread]` only | E_FAIL | repro | array bound alone fails |
| `numthreads-only` | `[numthreads(c2Thread.x, c2Thread.y, 1)]` only | E_FAIL | repro | attribute alone fails |
| `scalar-array` | `static const uint n = 64; S1[n]` | 0 | no-repro | a const **scalar** *is* an ICE |
| `scalar-numthreads` | `static const uint eight = 8; [numthreads(eight,8,1)]` | 0 | no-repro | …in the attribute too |
| `braced-init` | `static const uint2 c = {8,8}; S1[c.x*c.y]` | E_FAIL | repro | not the `uint2(...)` constructor |
| `hv2021` | repro at `-HV 2021` | E_FAIL | repro | not a language-version default |

So the two reported failures are **one defect with two faces**: reading a component of a
`const` vector is not a constant expression. `static const` itself is fine; the vector
constructor is not implicated (`braced-init` fails without one); and HLSL 2021 does not
change it.

`scalar-numthreads` is worth flagging separately. My prediction before running it was
`match` — it is the repro of cross-referenced **#2191** ("Assert when a static const uint
is used with `[numthreads]`"), which is still open. It compiled cleanly, exit 0,
`NumThreads=(8,8,1)`. The `--expect` on that variant was re-recorded as `no-match` after
the run so the stored expectation asserts the current behaviour rather than my wrong guess;
the wrong guess is recorded here instead of being quietly overwritten. **This is an
observation about
#2188's boundary, not a triage of #2191** — #2191 was not fetched, its history was not
bisected, and its scalar-assert claim may have applied to a shader shape not tested here.

## FXC

Measured rather than repeated from the label. `manual-case-fxc.txt`, produced by
`run-fxc.ps1` (compiler path from `$env:FXC` or discovered under the Windows SDK — no
hardcoded path), Windows SDK 10.0.26100.0 x64,
`Microsoft (R) Direct3D Shader Compiler 10.1`:

**All six shaders compile, exit 0**, and the disassembly shows the constants folded:

```
==== repro.hlsl  [the reported shader]
[exit] 0
dcl_thread_group 8, 8, 1
```

FXC has no SM6 profile, so `cs_5_0` is used instead of `cmd.txt`'s `cs_6_0`; that is
recorded in the capture's header. This confirms `fxc-disagrees` on measured evidence, and
confirms it for the *specific* construct rather than for the shader generally.

## History

`bisect --issue 2188 --linear`, all 20 bisectable releases, none skipped as unprobeable:

```
v1.4.1907 v1.5.2010 v1.6.2104 v1.6.2106 v1.6.2112 v1.7.2207 v1.7.2212 v1.7.2212.1
v1.7.2308 v1.8.2403 v1.8.2403.1 v1.8.2403.2 v1.8.2405 v1.8.2407 v1.8.2502 v1.8.2505
v1.8.2505.1 v1.9.2602 v1.9.2602.24 v1.9.2607        -- all: repro

result: always-repro'd across v1.4.1907..v1.9.2607
```

A `--linear` scan was used rather than the default binary search even though the thread
mentions no fix or revert, for a reason specific to this repro: **the shader has two
independent failure sites and `match.json` is `nonzero_exit`, so a fix to either half alone
would be invisible** — the surviving half keeps the exit status nonzero and the history
still reads "always". The scan does not by itself remove that risk, so each captured probe
was checked for both diagnostics:

```powershell
# from data/issues/2188/
Get-ChildItem out-*.txt | ForEach-Object {
  $t = Get-Content $_ -Raw
  '{0,-16} vla={1,-4} numthreads={2}' -f `
    [regex]::Match($t,'# compiler: (\S+)').Groups[1].Value,
    $(if($t -match 'variable length arrays are not supported in HLSL'){'yes'}else{'NO'}),
    $(if($t -match "'numthreads' attribute requires an integer constant"){'yes'}else{'NO'}) }
```

Both diagnostics are present in **all 21** captured probes (20 releases + `main-debug`).
Neither half was ever fixed, so the single-predicate history is sound.

One thing did change, and only in the diagnostics: the
`Group size of 0 (0 * 0 * 1) is outside of valid range` warning and the
`compute entry point must have a valid numthreads attribute` error first appear in
**v1.8.2403** (2024-03-07); v1.7.2308 (2023-08) and earlier print only the three errors.
Same rejection, more explanation. The 2019 report is otherwise word-for-word current —
v1.4.1907's output is identical to today's minus those two lines.

**The floor is v1.4.1907 (2019-07)**, which post-dates the report (2019-05). "Always" here
means "for as long as it is possible to check with released binaries", not "since it was
filed".

## Compiler Explorer

`https://godbolt.org/z/nvqTPYffM` — four panes on `repro.hlsl`: `fxc_10_0_19041`
(`/T cs_5_0 /E csMain`), `dxc_1_6_2112`, `dxc_trunk`, `hlsl_clang_trunk`. Verified by
fetching the page; the `godbolt-note.txt` banner renders as the first lines of the source.
FXC is there because the issue *is* a disagreement, and a link where FXC succeeds beside
DXC's two errors shows it rather than asserting it.

Full text of every pane is captured in `manual-case-ce.txt` (`run-ce.py`, which reuses
`triage.py`'s own `ce_compile`/`annotate`, so the capture is the same request the link is
built from). CE runs Release Linux builds and `dxc_trunk` is a rolling build, so this
corroborates the local run and does not overrule it.

**Clang, with its control.** SKILL.md requires a control before believing any
cross-compiler difference, so `control-inlined.hlsl` was compiled on the same four panes
first (`manual-case-ce-control-link.txt`, https://godbolt.org/z/6EaKfvf5z):
`hlsl_clang_trunk` **exit 0**, emitting DXIL with `!72 = !{i32 8, i32 8, i32 1}`. Clang
handles this shader, so its failure on the repro is evidence:

```
<source>:40:28: note: initializer of 'cThread' is not a constant expression
<source>:39:25: note: declared here
<source>:40:27: error: variable length arrays are not supported for the current target
<source>:42:2: error: 'numthreads' attribute requires an integer constant
<source>:43:6: error: missing numthreads attribute for compute shader entry
```

Clang HLSL **shares the gap**, and names the cause outright — the *initializer* is not a
constant expression. (clang version 24.0.0git, llvm-project 0b12400bd4f0; a rolling build,
so treat the exact wording as today's, not as a fixed fact.)

## Corroboration from source

Every excerpt below is captured verbatim in **`manual-case-source.txt`**, pinned with
`git show eff900d5:<path>` to the commit the ground-truth compiler was built from. The
working tree had already moved on to `f8220ace4` by the time I checked, so bare line
numbers against `main` will drift; use the captured file.

- `tools/clang/lib/Sema/SemaType.cpp:2144` — `err_hlsl_vla` fires whenever an HLSL array
  type is still a variable array type, i.e. whenever the size expression did not fold.
- `tools/clang/lib/Sema/SemaHLSL.cpp:13889` — `ValidateAttributeIntArg` tests
  `E->isCXX11ConstantExpr(...)` and, when that fails, diagnoses and **returns 0**.
  `AT_HLSLNumThreads` (SemaHLSL.cpp:14816) then computes `N = X*Y*Z == 0`, reports
  `warn_hlsl_numthreads_group_size` — the "Group size of 0" line — and *drops the
  attribute*, which is why a third error says the entry point has no `numthreads`.
- `tools/clang/test/SemaHLSL/const-expr.hlsl:365` asserts that `float arr_sc_One[sc_One]`
  with `static const uint sc_One = 1` is **accepted**, matching `variant-scalar-array`.
- `tools/clang/test/SemaHLSL/const-expr.hlsl:379-382` — the divergence is codified as
  expected behaviour, with FXC's answer recorded next to it:

  ```
  // Note: here dxc is different from fxc, where a const integral vector can be used in ICE.
  // It would be desirable to have this supported.
  float arr_vc_One[vc_One.x];  /* expected-error {{variable length arrays are not supported
                                  in HLSL}} fxc-pass {{}} */
  ```

  Note `vc_One` there is `static const uint1 vc_One = 1` — no vector constructor — which
  independently agrees with `variant-braced-init`.
- `tools/clang/test/SemaHLSL/attributes.hlsl:659` records the same thing for an attribute:
  `[maxvertexcount (sc_count4.w)]` → `expected-error ... fxc-pass {{}}`, while
  `[maxvertexcount (sc_count)]` with a `static const int` folds to 12.

So this is a known, deliberately-tested gap, not an accident: the tests would have to be
updated for any fix. Nobody has claimed it is *desired* behaviour — the test comment says
the opposite.

## Assessment

- **Status `repros`.** Same construct, same two diagnostics, same exit status as reported.
- **History `always-repro'd`** (v1.4.1907..v1.9.2607, floor post-dates the report).
- **Confidence high.** Positive predicate, negative control captured, every release probe
  inspected for both diagnostics, second compiler (FXC) measured, third (Clang) measured
  with its own control, and the behaviour is codified in DXC's own tests.
- **Suggested action `still-valid-keep-open`.** It is a live FXC divergence with a
  workaround (`#define`, per the 2019 comment) and no user-visible progress in 20 releases.
  Whether const vector components *should* be integer constant expressions is a language
  decision, and the successor compiler currently answers it the same way DXC does, so any
  change belongs in both. The comment states this without pre-empting it.
- Not a duplicate. #2530 (const **scalar** through a type conversion, `uint(ARRAY_SIZE)`)
  and #2191 (scalar in `[numthreads]`, which no longer reproduces in the shape tested here)
  are neighbouring cases of the same ICE-folding area, not the same defect.

### Labels

Now `bug, fxc-disagrees`; proposing to add `type-system` and `hlsl-next`, remove nothing.

- `type-system` ("Bugs relating to inconsistencies in HLSL's type system") — the finding
  is precisely an inconsistency: a `const` scalar is a constant expression, a component of
  a `const` vector is not, in both the roles this issue exercises.
- `hlsl-next` ("Bugs for consideration on next language version") — changing it changes
  what HLSL considers a constant expression, and DXC's own test says "It would be desirable
  to have this supported". Clang trunk agrees with DXC today, so this is language-level.
- Keeping `bug`: it is a defect, not a feature request, and FXC's behaviour is the
  baseline. Keeping `fxc-disagrees`: now verified by running FXC, not inherited.
- **Deliberately not proposing `check-in-clang`** ("See if this repros in clang as well").
  It reads as a to-do, and the check has been done — the result is in the draft comment and
  in `manual-case-ce.txt`. Adding it would queue work that is already finished. If the team
  uses it as a *finding* marker rather than a to-do, add it.
- Not `crash`: exit is E_FAIL, not an internal failure, and no assert fired in a Debug
  build. Not `diagnostic`: the message could be clearer — "variable length arrays are not
  supported" describes the consequence, not the cause, where Clang says "initializer of
  'cThread' is not a constant expression" — but that is a side observation, not the issue.

### What I could not determine

- **Whether the 2019 reporter saw these exact diagnostics.** They never quoted one, and
  v1.4.1907 (2019-07) is the oldest binary available — it post-dates the report by two
  months. The May-2019 compiler is not checkable.
- **Whether #2191's assert ever existed**, or in what shader shape. Its repro compiles
  clean here, but that issue was not triaged.
- **Effort or risk of a fix.** Nothing here measures that, and the `Dormant` milestone is
  an explicit product judgement that is not mine to revisit.

### Completeness self-check

`triage.py reindex` was withdrawn by the orchestrator mid-batch: its `--reset` defaults to
true, so it does `DELETE FROM issues; DELETE FROM runs;` and is unsafe while other workers
are writing (`method-notes.md` §2). I had already run it four times before that; the
database is derived data and will be rebuilt at collation, so no evidence was harmed.

Its completeness audit is replaced here by **`selfcheck.ps1` → `selfcheck.txt`**: 45
read-only assertions over this directory only, covering the required artefacts, a captured
output with an exit code for all 21 compilers probed, a declared expectation on all 7
variants, and — the important part — that every measurement quoted in this file and in
`comment.md` resolves to a matching string in a file on disk. It reports 0 failures.

Writing it caught one real omission: the source citations above had no captured artefact
and were pinned to nothing, which is why `manual-case-source.txt` now exists.
