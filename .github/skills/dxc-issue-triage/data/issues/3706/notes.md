# Triage note — #3706

**Passing uninitialized var as index to structure buffer causes undef being passed in dxil**

- URL: https://github.com/microsoft/DirectXShaderCompiler/issues/3706
- Filed 2021-04-22 by `vcsharma`; 0 comments; labelled `correctness`; milestone `Backlog`;
  assigned to `llvm-beanz` since 2022-01-07
- Batch: 009
- Repro quality: `complete`
- Status vs clean `main` Debug (1.9.0.5433, `ab5400907`): `repros`
- History: `always-repro'd` across v1.4.1907..v1.9.2607 (20 releases, linear scan, no
  invalid probes)
- Confidence: high
- Suggested action: `needs-human-judgement`
- Godbolt: https://godbolt.org/z/n9YeYKT3W (verified by reading the shortlink back)

## Ground truth

`main-debug` reports commit `ab5400907`, which HEAD (`111ac3828`) no longer contains after a
history rewrite. Verified by tree instead of by SHA, per SKILL.md:
`git diff --name-only ab5400907 HEAD` lists **984 files, 0 of them outside
`.github/skills/dxc-issue-triage/`** — no compiler source differs from HEAD, so the build is
valid ground truth for `main`.

## Configuration

The issue states no profile. Its quoted DXIL pins it: `dx.op.rawBufferLoad` (opcode 139) is
SM 6.2+, `dx.op.storeOutput` with an arbitrary `OUT` semantic is a vertex stage, and
`dx.op.createHandle` is pre-SM 6.6 binding. `-T vs_6_2 -E main` reproduces the reporter's
line **verbatim**:

```
%2 = call %dx.types.ResRet.i32 @dx.op.rawBufferLoad.i32(i32 139, %dx.types.Handle %1, i32 undef, i32 0, i8 1, i32 4)  ; RawBufferLoad(srv,index,elementOffset,mask,alignment)
```

`ps_6_x` is not available: `error: invalid semantic 'OUT' for ps 6.0`. `vs_6_0` reproduces
the same defect through the older op (`variant-vs60-main-debug.txt`), which is why the
predicate accepts both:

```
%2 = call %dx.types.ResRet.i32 @dx.op.bufferLoad.i32(i32 68, %dx.types.Handle %1, i32 undef, i32 0)  ; BufferLoad(srv,index,wot)
```

vs_6_2 was kept as the primary because it is what the report shows, and every release in the
catalog can express it — the linear scan produced no `invalid-probe`.

## What was measured

**1. The symptom is exactly as reported, and is silent.** All 21 probes (main-debug + 20
releases) exit **0**. Grepping every `out-*.txt` for `warning|error|invalid-probe|not
found|not signed` returns **nothing at all** — so no release diagnosed it, and no release
warned that `dxil.dll` was missing, which means the DXIL validator ran and accepted the
module in every one of them.

**2. The module validates and is signed.** Confirmed positively rather than inferred:
`control-uav-undef-store.hlsl` trips `ValidationRule::InstrUndefinedValueForUAVStore` on the
same command form with no `-Fo`, proving the validator really is in the pipeline:

```
error: validation errors
control-uav-undef-store.hlsl:16:11: error: Assignment of undefined values to UAV.
Validation failed.
```

That exits `0x80004005` (E_FAIL) — an ordinary diagnosed error, **not** an internal failure.

Its cross-release behaviour is itself a finding: **v1.4.1907 accepts the same undef UAV store
(exit 0)** while v1.9.2607 and `main` reject it. The validator has been tightened for `undef`
in one operand position at some point after v1.4.1907; only the two endpoints were probed, so
no boundary is claimed.

**3. The validator has no rule for this operand — corroborated from source.**
`lib/DxilValidation/DxilValidation.cpp` (`RawBufferLoad` case, ~line 1948) checks the
*elementOffset* operand and the alignment operand, and never inspects the **index** operand:

```cpp
case DXIL::ResourceKind::RawBuffer:
  if (!isa<UndefValue>(Offset)) { ... InstrCoordinateCountForRawTypedBuf ... }
case DXIL::ResourceKind::StructuredBuffer:
  if (isa<UndefValue>(Offset)) { ... InstrCoordinateCountForStructBuf ... }
```

`InstrUndefinedValueForUAVStore` ("Assignment of undefined values to UAV",
`utils/hct/hctdb.py:8470`) is only reached from UAV-store paths.

**4. DXC already has the front-end diagnostic; it is off by default.** This is the finding
that most changes what can be done about the issue.

```
$ dxc -T vs_6_2 -E main repro.hlsl -Wall
repro.hlsl:10:19: warning: variable 'j' is uninitialized when used here [-Wuninitialized]
repro.hlsl:9:11: note: initialize the variable 'j' to silence this warning
```

Source: `tools/clang/include/clang/Basic/DiagnosticSemaKinds.td:1573-1575` declares
`warn_uninit_var` as `InGroup<Uninitialized>, DefaultIgnore` — inherited unchanged from
upstream Clang, where the group is reached via `-Wall`. So this is a default-warning-set
question, not a missing analysis.

**5. …but the existing warning does not cover the whole space.**
`control-partial-init.hlsl` writes `j.x` and indexes with `j.y`. It emits the identical
`i32 undef` index, and **`-Wall` says nothing about it** (`variant-partial-init-wall-main-debug.txt`
contains no diagnostic line). Enabling `-Wuninitialized` by default would therefore address
the reported case and not the partially-initialized one.

**6. FXC rejects the identical source.** Compiler Explorer, `fxc_10_0_26100 /T vs_5_0 /E main`
(FXC has no 6.x profile; the source text is unchanged):

```
error X4000: variable 'j' used without having been completely initialized
```

**7. Clang (`hlsl_clang_trunk`, `-fsyntax-only`) is silent too.** The pane carries its own
control: Clang *does* diagnose the very same statement
(`warning: implicit conversion changes signedness: 'int' to 'unsigned int' [-Wsign-conversion]`
on `return stbuf[j].v;`), so Sema reached the expression and had nothing to say about `j`.
Without `-fsyntax-only` the pane is stage noise — `Unsupported intrinsic
llvm.dx.store.output.i32 for DXIL lowering`, `Cannot create RawBufferLoad operation: Invalid
stage` — which is about Clang's incomplete vertex backend, not about this issue.

## Predicate and controls

`match.json` is `all_of`:
1. `regex` — `undef` in the operand **immediately after the handle** (the index) of
   `dx.op.rawBufferLoad` or `dx.op.bufferLoad`. This is the positive anchor: a compile that
   emitted no DXIL cannot satisfy it.
2. `not_regex` — no `warning`/`error` line mentioning `uninitialized`, i.e. the "silently"
   half of the report.

Deliberately **not** "an `undef` inside the buffer-load call", which is the #3009 trap and is
live in this issue's own op.

| capture | expect | result |
| --- | --- | --- |
| `variant-initialized-main-debug` (`int j = 0`) | no-match | no-match — index is `i32 0` |
| `variant-byteaddress-main-debug` (correct ByteAddressBuffer) | no-match | no-match — its load reads `i32 %3, i32 undef`, undef in the *elementOffset* slot, which the validator **requires** |
| `variant-uav-undef-store-main-debug` / `-v1.4.1907` / `-v1.9.2607` | no-match | no-match |
| `variant-wall-main-debug` (repro under `-Wall`) | no-match | no-match — the warning falsifies clause 2 |
| `variant-vs60-main-debug` | match | match — same defect at SM 6.0 |
| `variant-partial-init-main-debug` | match | match |
| `variant-partial-init-wall-main-debug` | match | match — `-Wall` does not reach this form |

The inverse hazard (an absence clause falsified for free by output that echoes the token) was
checked directly rather than assumed: no `out-*.txt` contains the words `warning` or `error`
at all.

## Assessment

The symptom is real, unchanged since before the issue was filed, and present in every
probeable release. What it is *not* is a case of DXC miscompiling well-defined input: reading
an uninitialised variable is undefined in HLSL, and `undef` is a legal lowering of it. So the
question the issue actually poses — and which the reporter posed correctly — is whether DXC
owes a diagnostic, and where it belongs.

Three separable answers are on the table and all three are policy calls, not measurements:

- **Front end.** `-Wuninitialized` exists and is `DefaultIgnore`. Turning it on by default
  is cheap and would cover the reported shader — but not the partially-initialized form
  (measurement 5), so it is a partial answer.
- **Validator.** `microsoft/hlsl-specs#272` "Strict validator mode" was opened 2024-07-08 by
  this issue's own assignee, citing **this issue by number** as an example of IR generation
  the validator misses, and proposes an opt-in `-strict` mode rather than tightening the
  existing rules. That is the tracked home for the validator angle.
- **Language.** Whether this should be an error at all, as it was in FXC, is an HLSL
  decision.

That is why the suggested action is `needs-human-judgement` rather than
`still-valid-keep-open`: the measurement is settled and the choice is not.

### Relationship to #3009 — related, not a duplicate

Both issues are an uninitialised local reaching `undef` in DXIL with no diagnostic, and they
were filed ten months apart. They are nevertheless not one defect, on three independent
grounds:

1. **The remedies do not coincide.** The front-end check DXC already ships fires on #3706's
   wholly-uninitialised scalar and does **not** fire on the partially-initialised form that
   #3009 reports (`int2 b; b.x = a;` then use `b`) — measured here as
   `control-partial-init.hlsl` under `-Wall`, which produces no diagnostic. Enabling the
   warning by default would close #3706's reported case and leave #3009's open.
2. **The DXIL manifestations need different rules.** #3009's `undef` is an operand of an
   arithmetic op (`IMad`); #3706's is a resource **index**. A validator rule for either would
   not catch the other. The distinction is not cosmetic: the operand this issue is about sits
   one slot away from an operand where `undef` is *mandatory* for a ByteAddressBuffer.
3. **Maintainers have already routed them apart.** On #3009, `validation` stands with
   @damyanp's "the validator should be able to detect this". On #3706, @damyanp added
   `validation` on 2024-07-16T17:24:58Z and @pow2clk removed it and applied `correctness`
   16 seconds later; and it is #3706, not #3009, that hlsl-specs#272 cites.

`duplicate-of #3009` is therefore not the right call. A cross-reference between the two is
worth a maintainer's consideration, but that is a collation-level judgement.

### Not claimed

- Nothing about **runtime** behaviour of an undefined structured-buffer index. That needs a
  GPU and is out of scope for a compiler probe.
- No fix-boundary for the UAV-store validation rule: only v1.4.1907 and v1.9.2607 were
  probed for it.
- Compiler Explorer's DXC panes print `DXIL.dll not found`, so they do **not** corroborate
  the "module validates and is signed" claim; only the local build does.

## Labels

- now: `correctness`
- proposed add: `diagnostic`, `fxc-disagrees`, `incorrect-code`
- proposed remove: none

`diagnostic` ("Issues for diagnostics") matches the reporter's own ask and measurement 4.
`fxc-disagrees` is measured, not assumed. `incorrect-code` ("Issues relating to handling of
incorrect code") is what the shader is. `validation` is **not** proposed: it was deliberately
removed by @pow2clk in July 2024, and the validator angle is tracked in hlsl-specs#272.
`check-in-clang` was considered and left out: its description is an instruction ("See if this
repros in clang as well") and measurement 7 has already carried it out.

## Runs

| Compiler | Exit | Timed out | Verdict |
| --- | --- | --- | --- |
| main-debug | 0 | no | repro |
| v1.4.1907 | 0 | no | repro |
| v1.5.2010 | 0 | no | repro |
| v1.6.2104 | 0 | no | repro |
| v1.6.2106 | 0 | no | repro |
| v1.6.2112 | 0 | no | repro |
| v1.7.2207 | 0 | no | repro |
| v1.7.2212 | 0 | no | repro |
| v1.7.2212.1 | 0 | no | repro |
| v1.7.2308 | 0 | no | repro |
| v1.8.2403 | 0 | no | repro |
| v1.8.2403.1 | 0 | no | repro |
| v1.8.2403.2 | 0 | no | repro |
| v1.8.2405 | 0 | no | repro |
| v1.8.2407 | 0 | no | repro |
| v1.8.2502 | 0 | no | repro |
| v1.8.2505 | 0 | no | repro |
| v1.8.2505.1 | 0 | no | repro |
| v1.9.2602 | 0 | no | repro |
| v1.9.2602.24 | 0 | no | repro |
| v1.9.2607 | 0 | no | repro |

v1.6.2104 shipped 2021-04-20, two days before this issue was filed, and reproduces — so the
history covers the release the reporter would have been using, and v1.4.1907 (2019-07) puts
the behaviour ~21 months earlier still. v1.5.2003 was not probed by hand: the catalog hole it
leaves (2019-07 → 2020-10) closes well before this 2021 report.

`text_stale` is **not** set. The issue was filed 2021-04-22 and its title and body describe
precisely what the compiler does today, down to the named DXIL op.

## Evidence

- `expected.md` — symptom and decision criteria, written before anything was compiled
- `repro.hlsl`, `cmd.txt` — the reported shader and the exact arguments
- `match.json` — predicate, with the #3009 trap and both controls documented
- `control-initialized.hlsl`, `control-byteaddress.hlsl`, `control-uav-undef-store.hlsl`,
  `control-partial-init.hlsl` — controls, each with a captured `variant-*.txt`
- `out-<compiler>.txt` — 21 probes
- `manual-case-godbolt-verify.txt` — full text of all four Compiler Explorer panes
- `godbolt-note.txt` — the "what to look for" banner published with the link
- `comment.md` — draft comment (NOT posted)
- `method-notes.md` — observations about the method, for collation
