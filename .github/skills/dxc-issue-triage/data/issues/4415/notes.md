# #4415 — Validator needs to prevent invalid handle in AnnotateHandle

**Issue**: <https://github.com/microsoft/DirectXShaderCompiler/issues/4415> — filed 2022-04-25
by tex3d, labels `bug`, `validation`, no comments in the thread.

**Ground truth**: `main-debug`, a Debug build of `main` at `13730886e`, self-reporting
`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)`. The
version string embeds a fork-local SHA; the public commit is `13730886e`. Captured output is
left exactly as produced.

**Verdict**: reproduces, both asks, unchanged on every release that can run the shader, and on
Microsoft's signed shipping `dxil.dll` as well as on the validator built from this tree.

---

## The two asks

The body asks two different things and the title names only the second.

**Ask A — front end.** `CBV` is read inside its own initialiser and that is diagnosed as a
warning; the reporter asks whether it should be an error by default. This is a question to the
project, not a defect claim, so "still reproduces" here means only "unchanged since 2022".

**Ask B — DXIL validator.** The emitted module calls `dx.op.annotateHandle` with an invalid
(all-zero) handle, and DXIL validation accepts it. `validation` in this repo means DXIL
validation, so this is the headline.

Ask B is not a question about DXC's code generation. The validator's job is to reject bad DXIL
whoever produced it, so it must be probed with modules DXC never emitted, the way a
third-party producer would present them.

## Ask A — measured

`repro.hlsl` is the issue body verbatim (comments kept, so reported line numbers match), run
with the issue's own `RUN:` line.

```
$ dxc -T vs_6_6 -E main repro.hlsl
repro.hlsl:14:58: warning: variable 'CBV' is uninitialized when used within its own initialization [-Wuninitialized]
static ConstantBuffer<MyCB> CBV = ResourceDescriptorHeap[CBV.u];
                            ~~~                          ^~~
[exit] 0
```

Warning only, exit 0, DXIL produced. Ask A is exactly as filed.
Evidence: `out-main-debug.txt`, `out-main-debug--match-warning-only.txt`.

## Ask B — measured

### The compiler still emits the reporter's instruction, character for character

```
%1 = call %dx.types.Handle @dx.op.annotateHandle(i32 216, %dx.types.Handle zeroinitializer, %dx.types.ResourceProperties { i32 13, i32 4 })
```

and the compile ends `[exit] 0` with no `error: validation errors`. `dxc` runs the validator on
this path — see the liveness control below — so this alone is the validator accepting the
module. Evidence: `out-main-debug.txt`.

### Deliberately constructed modules are accepted too

`make-modules.py` builds every module below and echoes each command with
`subprocess.list2cmdline`, asserting the occurrence count of each textual patch. The doctored
modules start from `control-valid.hlsl` — the same shader with the initialisation order fixed —
so each differs from a known-valid module in one operand.

| module | `annotateHandle` handle operand | validator |
| --- | --- | --- |
| `emitted.ll` | `zeroinitializer` (DXC's own output) | **succeeded** |
| `zeroinit.ll` | `zeroinitializer` (patched into a valid module) | **succeeded** |
| `undefhandle.ll` | `undef` | **succeeded** |
| `valid.ll` | `%1` (untouched) | succeeded |

Evidence: `variant-*-main-debug-dxv4415--match-validator.txt`.

### The controls that make those acceptances mean something

`dxv` prints `Validation succeeded.` and nothing about what it validated, so that line alone is
also what a module with no `annotateHandle`, an unreadable file, and a run that never happened
all look like. Two defences:

1. **Self-test lines in the scored capture.** `validate.py` prints
   `module-annotatehandle-calls`, `annotatehandle-res-operands`,
   `annotatehandle-invalid-res-operand` and `module-requests-validator-version` before invoking
   `dxv`, and exits non-zero with `PARSE-WARNING` if the module cannot be read, holds no
   `dx.op` call, or holds no `annotateHandle`. The predicate scores those lines together with
   the `dxv` result, so a vacuous run cannot pass.
2. **Rejection controls**, proving the validator is live and discriminating:

| control | what it changes | result |
| --- | --- | --- |
| `control-checkedop-zeroinit.ll` | same operand value, on `textureLoad` | **rejected**: `Instructions should not read uninitialized value.` |
| `control-checkedop-undef.ll` | `undef` on `textureLoad` | **rejected**, same rule |
| `control-badprops.ll` | the **same** `annotateHandle`, invalid *props* operand | **rejected**, 4 errors |
| `control-undef-checked-op.ll` | `undef` on `cbufferLoadLegacy` | rejected, but by an internal cast error — see below |
| `control-validation-fails.hlsl` | bad root signature through plain `dxc` | **rejected**: `error: validation errors`, exit `0x80004005` |

The first two are the pair the verdict rests on: **the same invalid handle value, in the same
build, on a different opcode, is rejected by name.** The difference is the opcode, not the
value, not the module, not the harness.

`control-badprops.ll` closes the remaining gap: the validator *does* inspect that very
`annotateHandle` instruction — corrupt its `props` operand and it reports
`Constant values must be in-range for operation.` plus three consequent errors. It just never
looks at the handle operand.

### Microsoft's signed shipping validator behaves the same way

Everything above uses a validator built from this tree. The binary that actually gates shipping
shaders is Microsoft's signed `dxil.dll`, which nothing here builds. `signed-validator.py`
points `dxv` at the `dxil.dll` from the v1.8.2505.1 release archive
(`FileVersion 1.8.2505.32`, `Microsoft(r) Corporation`) via `DXC_DXIL_DLL_PATH`:

- **witness** (proving the external validator is really engaged, not the internal one):
  a module asking for validator version 1.10 is refused —
  `Validator version in metadata (1.10) is not supported; maximum: (1.9).`
- **control**: `textureLoad` + `zeroinitializer` → `Instructions should not read uninitialized value.`
- **subject**: `annotateHandle` + `zeroinitializer` → `Validation succeeded.`

Evidence: `manual-case-signed-validator.txt`.

## Why — from source

`lib/DxilValidation/DxilValidation.cpp`, `ValidateHandleArgs()`:

```cpp
case DXIL::OpCode::AnnotateHandle:
case DXIL::OpCode::AnnotateNodeHandle:
case DXIL::OpCode::AnnotateNodeRecordHandle:
case DXIL::OpCode::CreateHandleForLib:
  // TODO: add custom validation for these intrinsics
  break;
default:
  ValidateHandleArgsForInstruction(CI, OpCode, ValCtx);
  break;
```

`ValidateHandleArgsForInstruction()` is the rule the controls trip: "Make sure none of the
handle arguments are undef / zero-initializer", raising
`ValidationRule::InstrNoReadingUninitialized`. `ValidateHandleArgs` is called from
`ValidateDxilOperationCallInProfile` (`DxilValidation.cpp:2175`), so every opcode reaches it —
these four opt out.

`git log --all -S "ValidateHandleArgsForInstruction"` dates that check to `9468120e6`
(2023-07-21, Joshua Batista, PR #5399) — a year *after* this issue was filed, and it excluded
`AnnotateHandle` from the start. The exclusion is therefore deliberate and still outstanding,
not an oversight introduced later.

The second place `annotateHandle` is examined confirms the shape of the gap:
`lib/DxilValidation/DxilValidationUtils.cpp:326` walks every `annotateHandle` to build
`ResPropMap`, and checks only that the **props** operand yields a valid resource kind. The
handle operand is not examined there either.

## History

`bisect --linear` over the 20 stable releases, plus `release-matrix.py` which re-probes each
release with that release's own `dxc.exe` and `dxv.exe`:

| releases | result |
| --- | --- |
| v1.4.1907, v1.5.2010 | `invalid-probe` — `error: invalid profile vs_6_6`, predate SM 6.6 |
| v1.6.2104, v1.6.2106 | `no-repro`, **but for an unrelated reason** (below) |
| v1.6.2112 (2021-12-08) … v1.9.2607 (2026-07-29), 16 releases | repro |
| v1.8.2502 … v1.9.2607, the 6 releases shipping `dxv.exe` | doctored module **accepted** by that release's own `dxv` |

The two SM 6.6 *preview* releases lower `ResourceDescriptorHeap` to `createHandleForLib` rather
than `createHandleFromHeap`, and are rejected by a different rule entirely:

```
error: opcode 'CreateHandleForLib' should only be used in 'Library'.
```

That is an incidental catch by an unrelated check, not an invalid-handle rule that later
regressed. Treating those two rows as a fixed→broken transition would be wrong; `bisect` calls
the sequence "non-monotonic" for exactly this reason. From the first release in which SM 6.6
descriptor-heap indexing works as designed, the behaviour has never changed.

Each release row carries its own feature-presence control (a trivial `ps_6_6` texture load) and
each `dxv` row its own liveness control, so a row cannot read "accepted" because the release
could not run the probe.

## Incidental observation, not part of the verdict

`control-undef-checked-op.ll` puts `undef` on `cbufferLoadLegacy`, an opcode that *is* checked.
Validation fails, but with `Validation failed - error code 0x80aa001d` (`DXC_E_LLVM_CAST_ERROR`)
instead of a diagnostic: `GetCBufSize` does
`ValCtx.EmitInstrError(cast<CallInst>(CbHandle), ...)` at `DxilValidation.cpp:551`, and an
`undef` handle is a `Constant`, not a `CallInst`. So the validator reports a failure but loses
the message. This is a robustness detail of a *different* code path, it is not a crash of
`dxc` (the `dxv` process exits 1 and prints the code), and it does not bear on ask B — the
textureLoad controls carry that load instead. Recorded so the odd number in the captures is not
mistaken for something it is not.

## Assessment

Both asks are live and neither has moved since 2022.

Ask B is a genuine validator gap, confirmed three ways that do not share a failure mode: DXC's
own output, modules DXC never emitted, and the signed shipping validator. The exclusion is
explicit in source with a standing TODO, so no archaeology is needed to act on it — though
deciding *how* to reject (an invalid handle reaching `annotateHandle` may be better caught
where it is created) is a design call for the maintainers.

Ask A is a language/product decision — should `-Wuninitialized` on a resource in its own
initialiser be an error by default — and is not something triage can settle.

Labels `bug` and `validation` are both correct; no change proposed.

**Suggested action**: `still-valid-keep-open`.

## Files

| file | what it is |
| --- | --- |
| `expected.md` | written before any compiler ran: the decomposition, falsification criteria, and the source-derived prediction, recorded as a prediction |
| `repro.hlsl`, `cmd.txt` | the issue body verbatim and its `RUN:` line |
| `control-valid.hlsl` | the same shader, initialisation order fixed — base for the doctored modules |
| `control-checked-op.hlsl` | trivial `ps_6_6` texture load — base for the checked-opcode controls and the per-release feature-presence control |
| `control-validation-fails.hlsl` | proves the plain `dxc` path really validates (adapted from `tools/clang/test/DXILValidation/rootSigDefine10.hlsl`) |
| `make-modules.py`, `manual-case-make-modules.txt` | module generator and its transcript |
| `validate.py`, `validate.cmd` | validator harness, registered as compiler id `main-debug-dxv4415` |
| `release-matrix.py`, `manual-case-release-matrix.txt` | per-release dxc + dxv matrix with per-row controls |
| `signed-validator.py`, `manual-case-signed-validator.txt` | the signed `dxil.dll` probe, with its engagement witness |
| `match.json`, `match-warning-only.json`, `match-validator.json` | the three predicates, each carrying a note on why it is anchored |
| `out-*.txt`, `variant-*.txt` | every capture, headed by compiler, command, exit status and verdict |
| `godbolt-note.txt`, `manual-case-godbolt-verify.txt` | the Compiler Explorer banner and the verified panes |
| `method-notes.md` | what this issue taught about the method |
