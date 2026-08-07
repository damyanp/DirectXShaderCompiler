# #3259 Crash in TranslatePtrIfUsedByLoweredFn — triage notes

**Verdict: `repros`. History: always-repro'd (v1.5.2010 → v1.9.2607, 19 releases).
Repro quality: complete. Suggested action: still-valid-keep-open.**

Ground truth: `main-debug`, `C:\prj\DirectXShaderCompiler\build\Debug\bin\dxc.exe`,
commit `ab5400907`, version string verified before any measurement:

```
dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)
```

## The report

Filed 2020-11-12 by @jeffnn (contributor). A complete, self-contained repro plus the exact
invocation (`as_6_5`, `/Zi -enable-16bit-types /Qembed_debug`). An amplification-shader payload
containing a `Texture2D` is passed to `DispatchMesh`. The reporter states both halves clearly:
the input is invalid and should be diagnosed, and instead there is "an assertion failure and
then crash in TranslatePtrIfUsedByLoweredFn".

His same-day follow-up names the mechanism — `GetLoweredUDT` returns `nullptr` for a struct with
an embedded object type, and the caller does not check — and reports that adding a null check
locally produced `error: phi/select disallowed on pointers to local resources.` He did not say
the change was upstreamed, and it is not on `main` (see below).

The only other comment (@damyanp, 2024-07-09) is a bare cross-reference to another
amplification-shader issue. **No "still repros in version X" datapoint has ever been posted**,
so there was no prior observation to agree or disagree with.

`expected.md` was written from the issue text before any compiler was run.

## Repro and command

`repro.hlsl` is the issue body verbatim. `cmd.txt` is `-T as_6_5 -E main repro.hlsl`.

The filed flags were dropped and preserved in `cmd-as-filed.txt`. Justification, and the
evidence for it:

- they are incidental debug-info settings, not a workaround the reporter added to dodge some
  other bug, so there is no phase of the compiler being suppressed by keeping them;
- `variant-as-filed-main-debug.txt` runs the **exact filed command** and produces exactly the
  same failure (exit `0x80000003`), so nothing is lost by dropping them;
- every extra flag is another way an old release could reject the input and score as an
  `invalid-probe` rather than as a clean run (SKILL.md step 6). `-Qembed_debug` in particular is
  not present in the oldest releases in range.

`as_6_5` cannot be lowered further: `DispatchMesh` and amplification shaders are Shader Model
6.5, so this is already the oldest profile that can express the repro.

## Predicate

`match.json` is `internal_failure` — the kind SKILL.md step 4 mandates for `crash`-labelled
issues. This issue is a worked example of *why*, and the two candidate wrong predicates both
fail on measured data in this directory:

- **an assert-text predicate** (`!(Ty)`, `WrapInArrayTypes`, or `TranslatePtrIfUsedByLoweredFn`)
  scores all 19 probeable releases clean, because they are Release builds that access-violate
  instead of asserting — verdict would flip to a false "fixed in v1.5.2010";
- **a message-text predicate** on `access violation` would additionally miss **v1.5.2010**,
  which crashes with completely empty stderr (`out-v1.5.2010.txt`);
- **`nonzero_exit`** would score v1.4.1907 as reproducing, when it in fact prints
  `error: invalid profile as_6_5` and exits E_FAIL `0x80004005` — the ordinary diagnosed-error
  status, not a crash. It would also score a *correctly fixed* compiler as still broken, since
  the correct behaviour for this input is a diagnostic and therefore a nonzero exit.

Negative control: `control-scalar-payload.hlsl`, the identical shader with `uint value;` in place
of `Texture2D<float4> texture;`. Declared `--expect no-match`, captured on `main-debug` and on
both ends of the release range (v1.5.2010, v1.9.2607); all three exit 0 and emit DXIL.

## What was measured

| compiler | exit | shape |
| --- | --- | --- |
| `main-debug` (ab5400907, Debug) | `0x80000003` | trapped `DXASSERT` |
| v1.4.1907 | `0x80004005` | **invalid-probe** — `error: invalid profile as_6_5` |
| v1.5.2010 | `0xC0000005` | access violation, **stderr entirely empty** |
| v1.6.2104 … v1.9.2607 (18 releases) | `0xC0000005` | `access violation. Attempted to read from address 0x0000000000000000` |

Bisection was run `--linear` over all 20 releases rather than binary — every release was already
cached, and a full column is what makes the NDEBUG question below answerable rather than
inferred. Result: `always-repro'd across v1.5.2010..v1.9.2607 (1 release skipped as unprobeable)`.

`v1.5.2010` was released 2020-10-22, three weeks *before* this issue was filed. So "always
reproduced" here is not the usual "for as long as it is possible to check" caveat about the
v1.4.1907 floor — it means the defect has been present in every shipped compiler that has ever
been able to parse this shader, from before the report to today.

## The NDEBUG question, answered rather than assumed

The reported symptom is "an assertion failure **and then** crash", and every release binary is a
Release build with asserts compiled out. That is precisely the configuration in which
`never-repro'd-in-releases` would have been a measurement artefact rather than a fix.

**It is not an artefact here, and the reason is on disk.** The releases do not run clean — they
crash, at `0xC0000005`, reading address 0. The assert is only the first tripwire; the underlying
null type survives its removal. Concretely:

- `DXASSERT_NOMSG` expands to `do { } while (0)` under `NDEBUG`
  (`include/dxc/Support/Global.h:369-371`), so the Debug trap genuinely cannot occur in a
  release build;
- with it gone, `WrapInArrayTypes(nullptr, {})` returns `nullptr` (the loop body never executes
  for an unarrayed struct), and `ScalarReplAggregatesHLSL.cpp:450` calls
  `Builder.CreateAlloca(NewTy /* == nullptr */, ...)`.

So the Debug assert and the Release access violation are the same defect at two points on the
same path, and the release history is **meaningful evidence**, not a build-configuration
artefact. This is worth stating explicitly because the opposite conclusion has been drawn before
on an assert-shaped issue (#2191, where it genuinely was an artefact).

## Source corroboration

The reporter's 2020 diagnosis is unchanged on `main` at `ab5400907`:

- `lib/HLSL/HLLowerUDT.cpp:65-68` — `GetLoweredUDT` returns `nullptr` when a field is
  `dxilutil::IsHLSLObjectType` or `IsHLSLRayQueryType`: *"We cannot lower a structure with an
  embedded object type"*.
- `lib/HLSL/HLLowerUDT.cpp:70-72` — the same failure propagates out of a nested struct:
  `NewTy = GetLoweredUDT(ST); if (nullptr == NewTy) return nullptr; // Propagate failure back to root`.
- `lib/Transforms/Scalar/ScalarReplAggregatesHLSL.cpp:426` — the caller,
  `TranslatePtrIfUsedByLoweredFn`, takes the result with **no null check**.
- `:435` `if (Ty != NewTy)` is therefore taken (`nullptr != Ty`), and `:436`
  `WrapInArrayTypes(NewTy, ...)` hits `DXASSERT_NOMSG(Ty)` at `lib/DXIL/DxilUtil.cpp:877`.
- `:450` `Builder.CreateAlloca(NewTy, ...)` is the Release fault site.

The stack captured under cdb (`manual-case-assert-stack.txt`, re-runnable via `assert-stack.cmd`)
matches that reading exactly:

```
dxcompiler!hlsl::dxilutil::WrapInArrayTypes+0x5f
dxcompiler!TranslatePtrIfUsedByLoweredFn+0x266
dxcompiler!SROAGlobalAndAllocas+0x7b1
dxcompiler!SROA_Parameter_HLSL::runOnModule+0x8a7
```

`TranslatePtrIfUsedByLoweredFn` is the frame named in the issue title, so the title is accurate
and the issue text is **not stale**.

## Scope, measured

Two variants beyond the filed repro, both `--expect match`, both matching on `main-debug`:

- `variant-samplerstate-payload.hlsl` — a `SamplerState` member instead of a `Texture2D`. Same
  assert. The trigger is `IsHLSLObjectType`, not `Texture2D`.
- `variant-nested-object-payload.hlsl` — the `Texture2D` one level down inside a nested struct.
  Same assert, reached through the recursive `return nullptr` at `HLLowerUDT.cpp:72`.

In the other direction the defect is **narrow**: `IsPtrUsedByLoweredFn`
(`ScalarReplAggregatesHLSL.cpp:310`, switch at `:323-342`) admits only `IOP_DispatchMesh`'s
payload operand. `IOP_TraceRay`, `IOP_ReportHit` and `IOP_CallShader` are present but commented
out under `// TODO: Lower these as well, along with function parameter types`. No other
intrinsic reaches this path today — which also means enabling any of those TODOs would extend
the defect unless the null check goes in first.

## Compiler Explorer

<https://godbolt.org/z/8rxodd943> — verified: `dxc_1_6_2112` and `dxc_trunk` both exit 139
(`SIGSEGV`). CE runs Release builds, so it shows the access-violation face of the bug and not
the assert; `godbolt-note.txt` says so on the page. Unusually for a `crash`-labelled issue, CE
*can* show this symptom, because it is not assert-only. CE's oldest DXC (1.6.2112) is well
inside the always-broken window, so the link corroborates the local build but cannot date
anything; the release scan does that.

No Clang pane. Clang's HLSL front end has no amplification-shader support and no `DispatchMesh`,
so the pane would be errors about the stage rather than about the issue (SKILL.md step 7).

## Labels

Now: `bug`, `dxil`, `crash` — all three supported by the evidence and none proposed for removal.
The fault is in the DXIL lowering/SROA path (`lib/DXIL`, `lib/HLSL`, `lib/Transforms/Scalar`), so
`dxil` fits.

Proposed addition: **`incorrect-code`** ("Issues relating to handling of incorrect code"). The
input is invalid HLSL that ought to be diagnosed; the defect is that DXC crashes instead of
diagnosing it. That is the label that makes this findable alongside the rest of the
crash-on-invalid-input class.

Considered and rejected: `diagnostic` (the missing diagnostic is a consequence, and
`incorrect-code` states the situation more precisely); `experimental-mesh-nodes` (that label is
work-graph mesh nodes, not amplification shaders); `low-hanging-fruit` / `up-for-grabs` (an
effort and routing judgement that is a maintainer's to make, and the reporter's local null check
was never reviewed).

## Assessment

Still valid, keep open. The defect is a crash on invalid input, present in every shipped
compiler that can parse the shader, with an unchanged and precisely located root cause that the
reporter identified on the day he filed it. Nothing here is a triage question; it is waiting on
a fix.

One deliberate non-claim: the reporter's local null check produced
`error: phi/select disallowed on pointers to local resources.` That was not tested during this
triage — testing it would mean modifying DXC source, which the skill forbids — so nothing here
says whether it is the right fix or whether that is the right diagnostic. It is recorded as what
he observed in 2020, not as a validated remedy.
