# #2202 — Validation error "DXIL intrinsic overload must be valid"

Ground truth: `main-debug`, clean Debug build of `main` at `eff900d5`,
`dxc --version` → `dxcompiler.dll: 1.10(5422-eff900d5)(1.9.0.15422) - 1.9.0.15422 (main, eff900d54)`
(captured in `manual-case-version.txt`). Batch `batch-004`.

That file also records a discrepancy I checked rather than assumed: the working tree's
`HEAD` is `f8220ace`, three commits *after* the commit the compiler was built from. All
three are confined to `.github/skills/dxc-issue-triage/` (the triage workspace's own
commits), `eff900d5` is an ancestor of `HEAD`, and the two DXC source files cited below are
byte-identical between the two. So the binary is the specified ground truth and the source
citations describe the code it was built from.

## Verdict

**`repros`** on `main` (`eff900d5`), and on every release from the bisection floor
v1.4.1907 to v1.9.2607. Repro quality **`complete`** — the reporter's `test.txt` attachment
still downloads and compiles as-is.

## The repro and why `cmd.txt` departs from the report

`repro.hlsl` is the reporter's `test.txt`
(<https://github.com/microsoft/DirectXShaderCompiler/files/3206906/test.txt>) byte-for-byte,
`#if` blocks and tabs included.

The command as filed is `dxc -E ps_main -T ps_6_0 test.hlsl`, kept in `cmd-as-filed.txt`.
`cmd.txt` adds `-HV 2018`. That is not a change of configuration but a *preservation* of it:
the reporter compiled in 2019, when dxc defaulted to HLSL 2018. At today's default the front
end rejects the input before codegen:

```
$ dxc -T ps_6_0 -E ps_main repro.hlsl                    # variant-hv-default-main-debug.txt
repro.hlsl:11:33: error: condition for short-circuiting ternary operator must be scalar,
                         for non-scalar types use 'select'
[exit] 2147500037   (0x80004005, E_FAIL)
```

That probe never reaches the DXIL validator, so it is evidence of nothing — but it exits
E_FAIL with no predicate match, so the runner scored it `no-repro`. Left as the primary
command it would have produced a fabricated "fixed in v1.7.xxxx" verdict. This is SKILL.md
step 6's `invalid-probe` trap pointing *forwards* (a newer default rejecting older-language
source) rather than backwards; `classify()` does not currently detect that direction. See
`method-notes.md`.

Measured across every language version, all on `main-debug`:

| `-HV` | result | evidence |
| --- | --- | --- |
| 2016 | `DXIL intrinsic overload must be valid` — the reported symptom | `variant-hv2016-main-debug.txt` |
| 2017 | same | `variant-hv2017-main-debug.txt` |
| **2018** (`cmd.txt`) | same | `out-main-debug.txt` |
| 2021 (today's default) | front-end error: vector-condition `?:` requires `select` | `variant-hv2021-main-debug.txt`, `variant-hv-default-main-debug.txt` |
| 202x | compiles clean, all-`float` DXIL | `variant-hv202x-main-debug.txt` |

`-HV 2018` is also what `llvm-beanz` used when he re-confirmed the bug on 2024-06-11
(<https://godbolt.org/z/e54rbcoPn>, `-T ps_6_7 -HV 2018`).

## What reproduces, exactly

`out-main-debug.txt`:

```
$ dxc -T ps_6_0 -E ps_main -HV 2018 repro.hlsl
[exit] 2147500037
error: validation errors

repro.hlsl:11:13: error: DXIL intrinsic overload must be valid.
note: at '%13 = call double @dx.op.dot3.f64(i32 55, double %10, double %11, double %12,
      double 1.000000e+00, double 1.000000e+00, double 1.000000e+00)' in block '#0' of
      function 'ps_main'.
Validation failed.
```

Exit `2147500037` is `0x80004005` (E_FAIL). **This is a diagnosed error, not a crash.**
dxc returns E_FAIL for a plain syntax error, an invalid profile and a DXIL validation failure
alike, so `nonzero_exit` and `internal_failure` are both the wrong predicate here — the first
would also fire on the `-HV 2021` front-end rejection above, the second would invent a crash
nobody reported. `match.json` is a positive `contains` on the validator's own wording.

## The useful finding: codegen is at fault, not the validator

`-Vd` separates the two, and the answer is unambiguous
(`variant-vd-novalidate-main-debug.txt`, exit **0**):

```llvm
%10 = select i1 %7, double 1.500000e+02, double 1.000000e+02
%11 = select i1 %8, double 1.500000e+02, double 1.000000e+02
%12 = select i1 %9, double 1.500000e+02, double 1.000000e+02
%13 = call double @dx.op.dot3.f64(i32 55, double %10, double %11, double %12,
                                  double 1.0, double 1.0, double 1.0)  ; Dot3(ax,ay,az,bx,by,bz)
declare double @dx.op.dot3.f64(i32, double, double, double, double, double, double)
```

with `; Note: shader requires additional functionality: Double-precision floating point`.

Corroborated from source rather than inferred from output:

- `utils/hct/hctdb.py:2101-2104` declares `Dot3` with overload string `"hf"`. Per
  `process_oload_types`' own documentation, `"hf" means overloads for scalar half and
  float`; a double overload would need a `d`. `Dot2` and `Dot4` are also `"hf"`.
  **`dx.op.dot3.f64` is not a legal DXIL overload.**
- The rule fired is `Instr.Oload`, `utils/hct/hctdb.py:8278`:
  `self.add_valrule("Instr.Oload", "DXIL intrinsic overload must be valid.")`.
- `utils/hct/gen_intrin_main.txt:128` declares
  `$match<0, 1> numeric [[rn,unsigned_op=udot]] dot(in numeric<c> a, in $type1 b);` —
  `numeric` includes `double`, so Sema legitimately resolves a `double` `dot`, which DXIL
  has no way to express.

So `-Vd` is not a workaround: it produces a DXIL module no runtime will accept. The
validator is doing exactly its job, and the defect is upstream of it — in the type
resolution that makes the literal-float ternary `double`, and in the lowering that then
requests an overload DXIL does not have.

This is also the current *design*: PR #6543, "[DxilOp] Allow generation of illegal DXIL
operations" (merged 2024-04-26), "removes the IsOverloadLegal check in OP::GetOpFunc … it
will permit the generation of illegal DXIL operations. Subsequently, the validation should
catch these illegal DXIL operations". Generating the bad op and catching it in validation is
intended; picking `double` for this expression is the bug.

## Controls

Both are known-good inputs the predicate must not fire on, both declared with
`--expect no-match` so `reindex` re-checks them forever.

| control | source | result on `main-debug` |
| --- | --- | --- |
| `control-named-temp.hlsl` | the reporter's own `#if 0` "// Works" branch, verbatim | exit 0, clean |
| `control-float-suffix.hlsl` | the `150.0f`/`100.0f` workaround from comment 1 | exit 0, clean |

Both differ from the repro in exactly one way, and both pass. The predicate discriminates.
The `f`-suffix workaround the reporter was given in 2019 still works.

## History

`bisect` (binary) short-circuits: both endpoints reproduce. The thread contains a
*retracted* "looks like its fixed in v1.6.2112" on the linked #2432, so a `--linear` scan was
run anyway. It found one release that did not match — and inspecting it rather than trusting
the score is the whole finding:

```
v1.4.1907 repro   v1.5.2010 repro   v1.6.2104 repro   v1.6.2106 repro   v1.6.2112 repro
v1.7.2207 repro   v1.7.2212 repro   v1.7.2212.1 repro v1.7.2308 repro
v1.8.2403 NO-REPRO  <-- not a fix
v1.8.2403.1 repro v1.8.2403.2 repro v1.8.2405 repro   v1.8.2407 repro
v1.8.2502 repro   v1.8.2505 repro   v1.8.2505.1 repro
v1.9.2602 repro   v1.9.2602.24 repro v1.9.2607 repro
```

`out-v1.8.2403.txt`:

```
[exit] 3221225477
Internal compiler error: access violation. Attempted to read from address 0x00000000000000B0
```

`3221225477` is `0xC0000005`. **v1.8.2403 does not fix this; it crashes on it.** It is the
only release that does, `control-named-temp.hlsl` compiles fine there
(`variant-control-named-temp-v1.8.2403.txt`, exit 0), and `-Vd` crashes too
(`variant-vd-novalidate-v1.8.2403.txt`), so the crash is on this input's illegal-DXIL path
rather than a general breakage or a validator-only fault.

Fully explained by the release notes for v1.8.2403.1 (2024-03-22): *"Revert 'Fix crash in
DXIL.dll caused by illegal DXIL intrinsic. (#6302) (#6342)'"*, PR #6418. PR #6302 (which
fixed #6168) replaced an assert on an illegal DXIL op with an illegal-value return; shipped
in v1.8.2403 it turned this diagnosed error into an access violation; it was reverted for the
patch release and superseded on `main` by #6543. (Those release notes and PR bodies are
captured verbatim in `related-github.json`, so this paragraph is checkable without GitHub.)

Recorded as permanent, re-checked assertions rather than as prose, using `match-crash.json`
(`internal_failure`) on labelled variants so the primary probes are untouched:

| variant | declared | scored |
| --- | --- | --- |
| `variant-crash-signature-v1.8.2403.txt` | `--expect match` | `repro` ✓ |
| `variant-crash-signature-v1.8.2403.1.txt` | `--expect no-match` | `no-repro` ✓ |
| `variant-crash-signature-v1.4.1907.txt` | `--expect no-match` | `no-repro` ✓ |
| `variant-crash-signature-main-debug.txt` | `--expect no-match` | `no-repro` ✓ |

**History: always reproduced across v1.4.1907..v1.9.2607.** The floor is v1.4.1907
(2019-07), which is *after* this was filed (2019-05), so "always" means "for as long as it is
possible to check", not "since it was filed".

## The reporter's second complaint is stale

The issue also asks for a better message: *"I think some improved error message for this
would be useful (didn't get any line number or anything)"*. That half was fixed.
`diagnostic-history.txt`, derived from the probes:

```
v1.4.1907   at 0x1e216e8f720 inside block #0 of function ps_main DXIL intrinsic overload must be valid
v1.5.2010   Function: ps_main: error: DXIL intrinsic overload must be valid. Use /Zi for source location.
v1.6.2104   repro.hlsl:11:13: error: DXIL intrinsic overload must be valid.
...unchanged through main
```

A source location arrived in **v1.6.2104** and has been there since. What has not changed is
that the diagnostic is still a *post-codegen validation* error rather than a front-end one,
so it names a DXIL instruction rather than the expression that caused it.

## Compiler Explorer

<https://godbolt.org/z/v7WofnW4f> — four panes, verified by compiling each through CE's API
before the link was shortened; full output in `manual-case-godbolt-panes.txt`.

| pane | result |
| --- | --- |
| `dxc_1_6_2112 -T ps_6_0 -E ps_main -HV 2018` | `error: DXIL intrinsic overload must be valid.` |
| `dxc_trunk` same args | identical |
| `dxc_trunk … -Vd` | exit 0, emits `call double @dx.op.dot3.f64` |
| `fxc_10_0_19041 /T ps_5_0 /E ps_main` | exit 0 — `dp3 o0.xyz, r0.xyzx, l(1.000000, 1.000000, 1.000000, 0.000000)`, no double |

The FXC pane is the contrast: FXC compiles the same source in float and never promotes the
literal-float ternary to double. That measurement is what supports the `fxc-disagrees`
label; it matches the FXC/DXC divergence already documented on #2432 for `abs`.

CE runs Linux **Release** builds and corroborates the local Debug build; it does not
overrule it. `dxc_trunk` is a rolling build, so only the class of failure is quoted.

No Clang pane. The repro writes `SV_Target`, which Clang's DXIL backend cannot lower, so the
pane would have shown an error unrelated to this issue — the #1702 trap. `llvm-beanz` already
answered the Clang question on the thread in 2024, so nothing is lost.

## Relationship to other issues

- **#8208** (open) — `mul` on two `double4`s produces
  `call double @dx.op.dot4.f64` and the *same* `DXIL intrinsic overload must be valid`
  error. Same defect class at the same layer: an HLSL `dot`/`mul` that resolves to `double`
  has no DXIL lowering. #2202 differs only in how the `double` arises (implicit literal-float
  promotion rather than a declared `double` type). Not proposed as a duplicate — the fixes
  plausibly differ (type resolution vs. `mul` lowering) — but they should be looked at
  together.
- **#2432** (closed 2024-06-12, "This is fixed in HLSL 202x") — the same literal-float→double
  promotion, reported for `+` rather than `dot`. Consistent with `-HV 202x` compiling this
  repro clean. #2202 is *not* closed by that: it is open against the default language mode,
  where the promotion still happens, and the only reason `-HV 2021` does not show it is an
  unrelated front-end restriction on vector-condition `?:`.
- **PR #2636** ("Fix bug in implicit cast involving literal float expressions", `Fixes #2432`)
  was **closed unmerged** on 2023-07-08.

## Assessment

Still valid, keep open. Two separable pieces:

1. **Live and unfixed:** in the default language mode, a literal-float ternary resolves to
   `double`, `dot` picks a `double` overload DXIL cannot express, and the shader fails to
   compile. Only reachable at `-HV 2018` or older *for this particular shader*, because
   `-HV 2021` rejects the vector-condition `?:` for an unrelated reason — but the underlying
   promotion is not `-HV`-specific and #8208 shows the same DXIL-level gap reached without
   any literal-float involvement.
2. **Fixed:** the diagnostic has had a file/line/column since v1.6.2104.

What this triage did *not* establish: whether the intended fix is in type resolution
(don't promote to `double`), in overload resolution (don't offer a `dot` DXIL lowering has no
overload for), or a front-end diagnostic in place of a validation error. That is a product
decision.

## Evidence index

Everything asserted above is backed by a file in this directory. Each `out-*`/`variant-*`
file carries a header recording the compiler id, exe, exact command, exit code, predicate
and verdict, so any single probe can be re-run from the file alone.

| file | what it is |
| --- | --- |
| `expected.md` | the symptom as reported, written before anything was run |
| `repro.hlsl` | the reporter's test.txt, byte-for-byte |
| `control-named-temp.hlsl` | control: the reporter's own '// Works' variant |
| `control-float-suffix.hlsl` | control: same shader with explicit 1.0f/1.5f literals |
| `cmd.txt` | the primary command (pins -HV 2018; comment block explains why) |
| `cmd-as-filed.txt` | the command exactly as the issue filed it |
| `match.json` | primary predicate + why internal_failure/nonzero_exit are both wrong here |
| `match-crash.json` | secondary predicate for the v1.8.2403 crash; labelled variants only |
| `manual-case-version.txt` | ground-truth dxc --version and the HEAD-vs-build-commit check |
| `out-main-debug.txt` | the primary result on main |
| `out-v1.*.txt (20 files)` | the same command on every cached release |
| `out-v1.8.2403.txt` | the access violation a linear scan scores as 'clean' |
| `variant-vd-novalidate-*.txt` | -Vd: compiles clean, emits dx.op.dot3.f64 -- the key finding |
| `variant-hv*.txt` | -HV 2016/2017/2021/default/202x on main |
| `variant-control-*.txt` | controls, with declared --expect |
| `variant-crash-signature-*.txt` | crash predicate asserted on 4 compilers, with declared --expect |
| `diagnostic-history.txt` | validator wording per release; backs the v1.6.2104 claim |
| `manual-case-godbolt-panes.txt` | full output of all 4 Compiler Explorer panes |
| `godbolt-note.txt` | what to look at in each pane |
| `related-github.json` | verbatim PR/issue/release records cited above |
| `issue.json` | the fetched issue and its comments |
| `notes.md / comment.md` | this write-up and the draft (unposted) reply |
| `method-notes.md` | observations about the procedure, for collation |
