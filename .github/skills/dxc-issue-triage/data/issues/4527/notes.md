# Issue 4527 — triage notes

**Verdict:** `changed-behavior` — the construct is still broken on `main`, but not in the shape
the report describes. Every stock configuration I could run **rejects the shader at compile
time**; nothing silently produces the bad bytecode the reporter took to a D3D12 device.

**Ground truth:** `main-debug` = local Debug build, `dxcompiler.dll 1.9.0.5433`, source identical
to public commit **`13730886e`**. **History:** reproduces on every probeable stable release from
**v1.4.1907 (2019-07)** through **v1.9.2607** and on `main` — 20 releases plus ground truth.

---

## 1. What was tested

| file | what it is |
| --- | --- |
| `attachment-test_dxc_bug.hlsl.txt` | the reporter's attachment, downloaded from the issue |
| `repro.hlsl` | byte-identical copy of that attachment (SHA-256 compared, equal) |
| `control-member-const.hlsl` | same file, `TEST_CASE` = `CASE_MEMBER_FUNCTION_CONST` (workaround 1: drop `static`) |
| `control-global-static.hlsl` | same file, `TEST_CASE` = `CASE_GLOBAL_FUNCTION_STATIC` (workaround 2: free function) |
| `control-global-scope-static.hlsl` | workaround 3, hand-written: the array at global scope |
| `variant-mesh.hlsl` | same file, `TEST_SHADER_TYPE` = `SHADER_TYPE_MESH` (the reporter's other symptom) |
| `repro-min.hlsl` | minimal restatement with no mesh syntax, so releases older than mesh shaders can be probed |
| `repro-cs.hlsl` | compute restatement + `-D CONTROL_NO_STATIC` guard, published to Compiler Explorer |

The two `control-*` files that come from the attachment were produced by byte replacement that
preserves every line and column, so diagnostics keep their line numbers.

**Command** (`cmd.txt`): `-T ps_6_0 -E mainPS repro.hlsl`. The issue supplies **no** command
line — no profile, no entry point, no flags — so `ps_6_0`/`mainPS` are mine, chosen because the
attachment ships configured as `CASE_MEMBER_FUNCTION_STATIC` + `SHADER_TYPE_PIXEL` and the title
names the pixel-shader failure. No `-Fo`, per the workspace convention; container-level questions
are answered separately in `manual-case-unsigned-container.txt`, which does use `-Fo`.

**Predicate** (`match.json`): `all_of` of

- regex `External declaration '[^']*kValues[^']*' is unused`
- contains `Validation failed.`

Rationale and rejected alternatives are recorded in the file's `note`. Briefly: the regex spans
none of the parts that move between releases (v1.4.1907 prints the detail lines with no `error:`
prefix, no trailing period and raw pointer addresses; v1.5.2010 appends `Use /Zi for source
location.`; v1.6.2104+ prefixes `file:line:col`). `Validation failed.` is the anti-vacuity
anchor — a shader that fails to *parse* cannot reach validation, so a broken probe cannot score
a match for free. `internal_failure` was deliberately **not** used: see §7.

## 2. Ground truth (`out-main-debug.txt`, verdict `repro`)

```
error: validation errors

error: External declaration '\01?kValues@?1??GetTestValue@MyClass@@QAA?AV?$vector@M$02@@I@Z@4QBV3@B' is unused.
error: Vector type '<3 x float>' is not allowed.
error: Vector type '<3 x float>' is not allowed.
repro.hlsl:93:16: error: Instructions must be of an allowed type.
note: at '%6 = extractelement <3 x float> %5, i64 0' in block '#0' of function 'mainPS'.
Validation failed.
```

Exit `2147500037` = `0x80004005` = **E_FAIL**, and no output file is written. This is an
ordinary diagnosed error, not a crash (§7).

The mesh entry point fails identically (`variant-mesh-main-debug.txt`,
`-T ms_6_5 -E TestDxcBugMS`), which covers the report's second symptom,
`CREATEMESHSHADER_INVALIDSHADERBYTECODE`.

## 3. Controls — all three reporter workarounds still work

| capture | file | exit | verdict |
| --- | --- | --- | --- |
| `variant-control-member-const-main-debug.txt` | `const` instead of `static const` | 0 | no-repro |
| `variant-control-global-static-main-debug.txt` | free function instead of member function | 0 | no-repro |
| `variant-control-global-scope-static-main-debug.txt` | array at global scope | 0 | no-repro |

Each emits a full disassembly, so the compile really happened; each was run with
`--expect no-match`, so a predicate that matched everything would have been caught here. The
global-scope control also produced a **signed** container (digest `8a90024852f6…`, non-zero) in
`manual-case-release-matrix.txt`, which is what makes the signing instrument in §5 trustworthy.

So exactly one variable separates failing from passing: a `static` local array inside a member
function. That is the reporter's claim, unchanged.

## 4. Release history — `always-repro'd`

`bisect --issue 4527 --linear` over `repro.hlsl`: **19/19** stable releases from **v1.5.2010** to
**v1.9.2607** match (`out-v1.*.txt`). Five prereleases are excluded by policy and `v1.2.0-alpha`
ships no `dxc` asset.

`v1.4.1907` is **unprobeable with the reporter's file** — it predates mesh shaders and answers
`unknown type name 'indices'` / `use of undeclared identifier 'SetMeshOutputCounts'` while
parsing the unused mesh entry point. That is an invalid probe, not a clean run, and `bisect`
classified it as such. `manual-case-release-matrix.txt` re-runs the whole matrix on
`repro-min.hlsl`, which contains no mesh syntax, and **v1.4.1907 fails too** — with the same
validation rule, in its era's wording:

```
External declaration '\01?kValues@…' is unused
Vector type '<3 x float>' is not allowed
at 0x… inside block #0 of function mainPS Instructions must be of an allowed type
```

So the defect predates the oldest release binary available; there is no window in which it was
introduced, and nothing to bisect. The matrix ends with the global-scope control compiling,
validating and signing on the same build, so "everything fails" is excluded.

## 5. The report's first clause — "compiles successfully with no errors"

I could not reproduce it in any stock configuration, including on **v1.7.2207** (2022-07-18), the
stable release nearest the report's 2022-06-22 build. It errors exactly like `main`.

Two configurations *do* produce a container (`manual-case-unsigned-container.txt`):

- **`-Vd`** (validation disabled): both `main` and v1.7.2207 exit 0 and write a container whose
  digest is all zeros — *unsigned*, matching the D3D12 message "Pixel Shader is unsigned" — and
  standalone `dxv` then rejects the DXIL inside it. **Control:** a known-good shader compiled
  with `-Vd` is *also* unsigned, because `-Vd` disables signing for everything; what separates the
  two is that the control's DXIL validates. "Unsigned" alone is therefore not evidence of this
  bug, and I do not treat it as such.
- **`dxil.dll` absent** (v1.7.2207 `dxc.exe` + `dxcompiler.dll` copied into an otherwise empty
  directory): warns `DXIL.dll not found`, then **still fails** — the in-process validator catches
  it. So a missing `dxil.dll` does not explain a silent compile. Compiler Explorer's `dxc_1_6_2112`
  pane independently shows the same combination: the not-found warning followed by the same
  validation errors.

Stated neutrally: the reporter's toolchain produced an object where mine produces a diagnostic.
The issue records no command line, so which configuration that was is not knowable from here, and
I make no claim about it.

## 6. Where it goes wrong — corroborated from source

`-fcgl` (`variant-fcgl-main-debug.txt`) and the `-Vd` disassembly
(`variant-vd-disasm-main-debug.txt`) both show the front end emitting the array **correctly, with
its initializer**, but with C++ inline-variable linkage:

```llvm
$"\01?kValues@…" = comdat any
@"\01?kValues@…" = linkonce_odr constant [3 x <3 x float>] [<3 x float> <float 0.0, …>], comdat, align 4
```

`dxilutil::IsStaticGlobal()` requires **`InternalLinkage`** (`lib/DXIL/DxilUtil.cpp:114-117`), so
a `linkonce_odr` global is invisible to everything keyed on it:

- `LowerTypePass::runOnModule` (`lib/Transforms/Scalar/LowerTypePasses.cpp:149-155`, "Work on
  internal global") never lowers the `<3 x float>` element type — hence
  `Vector type '<3 x float>' is not allowed`;
- the validator (`lib/DxilValidation/DxilValidation.cpp:4035-4038`) classifies it as *external*,
  and an external global with instruction users raises `DeclNotUsedExternal`
  (`:4087-4091`, message text at `utils/hct/hctdb.py:9115-9116`) — hence
  `External declaration '…kValues…' is unused`.

`manual-case-container-symbol.txt` measures that A/B directly, by disassembling the emitted
container with `-dumpbin` and printing every module-scope global in it:

| source | global as serialized into the container |
| --- | --- |
| `static` local in a member function | `@"\01?kValues@…" = linkonce_odr constant [3 x <3 x float>]` |
| same array at global scope (control) | `@kValues.v.1dim = internal constant [9 x float]` |

One word of linkage decides it. The control's array reaches the container **flattened to
`[9 x float]`** — that is `LowerTypePass` having run on it — while the failing one keeps its
illegal `<3 x float>` element type because the pass skipped it.

Other callers that would equally skip such a global: `DxilPreparePasses.cpp:1052`,
`DxilPromoteResourcePasses.cpp:513`, `HLLegalizeParameter.cpp:159`, `HLMatrixLowerPass.cpp:235`,
`ScalarReplAggregatesHLSL.cpp:1713/1808/6634`, `CGHLSLMSFinishCodeGen.cpp:2190`.

**Note on the wording, because it misleads:** "External declaration … is unused" is the
validator's classification of *non-internal linkage*, not a statement that the initializer was
dropped. The `-dumpbin` capture above shows the full initializer present in the container. An
earlier working hypothesis of mine — that the definition is lost during container serialization —
is **disproved** and does not appear in the draft comment.

There is no test in `tools/clang/test` covering a `static` local inside a member function, and no
commit in the history matches a fix in this area.

## 7. Exit codes: diagnosed error vs internal failure

Every failing run in this issue exits `0x80004005` (**E_FAIL**), which on Windows is what `dxc`
returns for an ordinary diagnosed error — a plain syntax error returns it too. Nothing here
asserted, trapped (`0x80000003`) or faulted (`0xC0000005`); no run timed out; the process always
printed a rule-named diagnostic and exited cleanly. I therefore did **not** use an
`internal_failure` predicate, and I do not describe this as a crash. The predicate keys on the
diagnostic text plus `Validation failed.`, which is only reachable when the compiler ran to
completion and the validator rejected the module.

The invalid-probe direction was the live risk instead, and it materialised once: v1.4.1907's
parse failure (§4) would have scored `no-repro` and manufactured a "fixed in v1.5" story if it
had not been classified as unprobeable and re-tested with a feature-presence control.

## 8. Other backends

- **SPIR-V** (`variant-spirv-main-debug.txt`): `-spirv` on the same source exits 0. The defect is
  specific to the DXIL path.
- **Clang** (Compiler Explorer, `hlsl_clang_trunk` pane): compiles the compute restatement, exit
  0, and its IR shows the same `linkonce_odr` global **already scalarized** to `[9 x float]` —
  i.e. its pipeline lowers the array without gating on internal linkage, reaching the same shape
  DXC only reaches for `internal` globals (§6). CE's Clang pane emits IR and does not run the DXIL
  validator, so this shows codegen accepting the construct, not that a container would validate.
  Because Clang already handles it, I did *not* propose the `check-in-clang` label; the check is
  done and its result is above.

## 9. Compiler Explorer

<https://godbolt.org/z/oYrbGzGq3> — four panes over `repro-cs.hlsl`, verified by
`triage.py godbolt` before shortening and re-read afterwards (`manual-case-godbolt-verify.txt`):

| pane | args | result |
| --- | --- | --- |
| `dxc_1_6_2112` | `-T cs_6_0 -E main` | fails; also warns `DXIL.dll not found` |
| `dxc_trunk` | `-T cs_6_0 -E main` | fails, same four errors |
| `dxc_trunk` | `+ -D CONTROL_NO_STATIC` | compiles |
| `hlsl_clang_trunk` | `-T cs_6_0 -E main` | compiles |

A compute restatement was necessary because Clang's HLSL backend cannot lower `SV_Target`; a
pixel pane would have filled with stage errors that say nothing about this issue. The restatement
was verified locally first — `variant-compute-main-debug.txt` (repro, E_FAIL) and
`variant-compute-control-main-debug.txt` (clean, exit 0) — so the CE panes are not the only
evidence for it. CE's oldest DXC is 1.6.2112, so the link corroborates current behaviour; the
dating comes from the local release matrix.

## 10. Assessment against `expected.md`

`expected.md` decomposed the runtime symptom into (A) the compile is clean and (B) the container
is invalid or unsigned, and pre-registered "**not-A ⇒ `changed-behavior`**". Measurement gives
**not-A**: the compiler diagnoses the input. B is confirmed only in the `-Vd` configuration, where
the emitted DXIL genuinely fails standalone validation.

- **status** `changed-behavior` — still misbehaves (valid HLSL is rejected), differently from the
  report (which describes a clean compile and a runtime rejection).
- **repro-quality** `partial` — as pre-registered: complete self-contained source with its own
  controls, but no command line and no way to observe the reported runtime failure.
- **history** `always-repro'd` — v1.4.1907 → `main`; predates every available binary.
- **confidence** `high` — 21 builds, three controls, a source-level mechanism, and an independent
  standalone-validator check.
- **suggested action** `still-valid-keep-open` — the underlying defect is real and unfixed, and
  the 2024-04-23 maintainer question ("is this still an issue?") now has a measured answer.
- **text-stale** — the body's "compiles successfully with no errors" does not describe any stock
  configuration I could measure, on `main` or on the release nearest the report.

## 11. Labels

The issue carries none. Proposed: **`bug`** ("Bug, regression, crash") — valid HLSL is rejected on
every release measured, with a mechanism identified in source.

Considered and not proposed: `incorrect-code` is about handling *invalid user code* and this
source is valid; `validation` ("related to validation or signing") describes the surface but the
defect is in a codegen pass that skips the global, and the label would mis-route it;
`correctness` is for shaders that run and produce wrong results, whereas today nothing is emitted;
`check-in-clang` is answered in §8. `needs-triage` is a maintainer's call, not mine.

## 12. Limits

- No D3D12 device in scope, so the reported `CreatePipelineState` rejection is not directly
  observable. The compiler-side facts (invalid DXIL, unsigned container under `-Vd`) are
  consistent with it, but they are not the same measurement.
- The reporter's 2022 command line and toolchain layout are unknown and unknowable from the
  issue; §5 says which configurations I tried and what each did, and stops there.
- `dxv.exe` and `dxc.exe` here are from the same build and share code. The DXIL validation result
  is therefore one witness plus a source citation, not two independent implementations. Compiler
  Explorer's Linux Release `dxc_trunk` reaching the same diagnosis is the closest thing to a
  second instrument, and it is still the same codebase.
- Nothing here dates the *first* broken release: v1.4.1907 is the oldest binary that can express
  the construct at all, and it already fails.
