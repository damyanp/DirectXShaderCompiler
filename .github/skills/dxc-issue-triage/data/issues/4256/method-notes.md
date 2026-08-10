# Method notes from #4256

Observations that should change how a future batch runs, not findings about the
issue itself.

## `dxv.exe` ships in only four stable releases — validator history is short

`release-matrix.py` walked every catalogued release. Thirteen of them
(v1.4.1907, v1.5.2003, v1.5.2010, v1.6.2104, v1.6.2106, v1.7.2207, v1.7.2212,
v1.7.2212.1, v1.8.2403, v1.8.2403.1, v1.8.2403.2, v1.8.2405, v1.8.2407) ship
`dxc.exe` and `dxcompiler.dll` but **no `dxv.exe`**. Only v1.8.2505, v1.9.2602,
v1.9.2602.24 and v1.9.2607 have one.

Any issue whose symptom needs the validator driven over a module DXC did not
produce therefore has a history window starting at v1.8.2505, no matter how old
the report. That is worth stating in `SKILL.md` next to the existing remark about
`dxl.exe`, so the next agent budgets for it instead of discovering it after
building a matrix. The substitute for the earlier period is source dating.

Worth checking whether `dxcompiler.dll`'s `IDxcValidator` could be driven
directly from a small Python/C++ harness against the *older* releases — that
would recover the pre-2505 window for validator issues generally. Not attempted
here; `dxv` was sufficient for the window that mattered.

## Validator-version metadata silently invalidates every release probe

The first release matrix looked like a clean, uniform result: every module on
every release "failed validation". It was measuring nothing. The modules carry
`!dx.valver = !{i32 1, i32 10}` from a `main` build, and every shipped validator
caps at 1.9, so all six cases returned

```
error: Validator version in metadata (1.10) is not supported; maximum: (1.9).
```

before looking at anything. The positive control is what caught it — `full.ll`,
unmodified DXC output, must validate, and it did not.

Generalisation worth adding to the `invalid-probe` material: **when a probe
carries a `.ll`/`.dxil` artifact built by one compiler to a different, older
compiler, the artifact has a version floor.** Emit the artifact set with
`-validator-version <lowest in the matrix>` and run an equivalence control on
ground truth. This is the same shape as the existing "a tool that never ran the
test still returns something that looks like an answer" trap, one layer out — and
it is invisible unless a positive control is in the matrix, which is a second
argument for the per-release control rule.

## A harness's output must be redacted at generation time, not afterwards

`validate.py` initially printed the absolute path of the `dxv.exe` it invoked, so
every capture contained a machine-local `…\build\Debug\bin\dxv.exe` under the
checkout root — which `scripts/check_paths.py` rejects, with exact allowlist
counts. (The full literal is deliberately not reproduced here: this file is
committed, and quoting it would itself trip the gate.)

The fix could not be to edit the captures: a capture is evidence, and hand-editing
one is falsification. It had to be to fix the harness and re-run everything. That
cost a full re-capture of nine files.

Suggestion: the harness-as-compiler section of `SKILL.md` should say, at the point
where it tells you to write the harness, that **any path the harness prints must
already be in `<repo>`/`<triage>` form**, and that `display_exe`'s convention is
the one to copy. A one-line pre-flight — run the harness once, pipe it through
`check_paths.py`'s pattern — before capturing anything would have caught it for
free.

## `retarget_cmd` only recognises `.hlsl`, so module-input issues lose variant subjects

`triage.py`'s `retarget_cmd` substitutes the shader token only when it ends in
`.hlsl`. For an issue whose subject is a `.ll` module, `--shader` cannot be used
at all; every variant has to go through `--args "<file>"`, which replaces the
whole argv. The capture then records `# variant: <label> (?)` because the tool
cannot tell what the subject was.

That is cosmetic but it costs a reader the one line that says which module a
capture is about — recovered here only because the harness prints
`[module] <name> (<n> bytes)` itself. If `retarget_cmd` learned `.ll` (or took an
explicit `--subject`), the variant headers would carry it. Meanwhile: **a harness
should always echo its own input filename**, for exactly this reason.

Related: `audit`'s "every `.hlsl` in the directory needs a captured variant" rule
is satisfied here only by the `control-dxc-pipeline` variant, which passes
`repro.hlsl` through the harness. That control is worth having anyway, but it is
worth knowing that it is doing double duty.

## A control can fail for a reason that is not the one you wanted

The natural fourth doctored module was `badflags.ll` — clear the ViewID bit in the
shader flags while leaving the ViewID op in the body. It exits **0x80000003**, a
Debug assert, almost certainly
`DXASSERT(ComputeSeriaizedViewIDStateSizeInUInts(...))` at
`DxilContainerAssembler.cpp:648`: the serialized array is 11 UINTs and a
non-ViewID shader expects 10.

That is an assert in the *container assembler*, reached before validation, on a
module no producer would emit. Scoring it as a crash would have been wrong on two
counts, so it was discarded and `make-modules.py` does not generate it. Recorded
because the shape recurs: when a hand-edited module trips an assert, ask which
component asserted before deciding what it shows.

## `dxv` is the right instrument for "a third-party tool produced this DXIL"

Worth promoting into `SKILL.md`'s instrument list. `dxv <file>.ll` assembles with
`IDxcAssembler::AssembleToContainer` and then runs `IDxcValidator::Validate` —
which is exactly the position an external DXIL producer occupies, and it takes a
module the compiler never made. Two caveats to record with it:

- it exits **1** on validation failure, not `E_FAIL`, so the exit-code table's
  0x80004005 row does not apply to it;
- it uses the **internal** validator from `dxcompiler.dll` unless
  `DXC_DXIL_DLL_PATH` names an absolute path to a signing `dxil.dll`
  (`lib/DxcSupport/dxcapi.extval.cpp`, `DxcDllExtValidationLoader::InitializeForDll`).
  The build tree contains a `dxil.dll` that is **not** used by default. Any
  capture involving `dxv` should print that variable's value, as `validate.py`
  does, or the reader cannot tell which validator ran.
- on a `.ll` input it never writes an output container (`Source was not a
  DxilContainer, no output file written`), so PSV0 content cannot be dumped from
  that path. `dxa` has no assemble mode, `dxc` treats `.ll` as HLSL, and `dxopt`
  failed with 0x80070002. If a future issue needs the emitted PSV0 bytes, that
  gap needs a different tool.

## Cross-issue

Nothing. #4256 has no cross-references in its timeline and no comments, and no
other issue in this batch touched ViewID state. Recorded so that the absence is
distinguishable from not having looked.
