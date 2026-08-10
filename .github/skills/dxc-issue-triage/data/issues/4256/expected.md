# #4256 — expected symptom

**Title:** DXIL validation should run ComputeViewIdState pass
**Filed:** 2022-02-13 by jenatali (Jesse Natalie). No comments. No labels. Milestone `Backlog`.

Written **before** running any compiler, from the issue text only.

## What the issue says

Quoting the body in full, decomposed:

| # | Ask / claim | Kind |
| --- | --- | --- |
| A | "The serialized view ID state in the DXIL module is not validated against the rest of the contents of the module." | claim about current validator behaviour |
| B | "Tools that produce DXIL (like the Mesa DXIL writer) can just not emit a view ID metadata node, even though they're using view ID, and validation will succeed." | claim about current validator behaviour |
| C | "This also includes the input -> output dependency mapping data, which can just be omitted entirely without affecting validation." | claim about current validator behaviour |
| D | "If drivers need this data, it should be validated as part of the validator." — i.e. the title's ask: **DXIL validation should run the `ComputeViewIdState` pass** | feature request (validator enhancement) |

This is an **enhancement request against the DXIL validator**, not a bug report about a
miscompile or a crash. The reporter is a Microsoft engineer who writes a *third-party* DXIL
producer (Mesa's DXIL writer), so the "producer" in claims B and C is not `dxc` — it is any
tool that hand-builds a DXIL module and then calls the validator. `dxc` itself always runs
`ComputeViewIdState` on its own output, so a plain `dxc` compile can never exhibit B or C.
The measurement therefore has to construct the module the reporter describes.

## What "this reproduces" means

Because the ask is for behaviour that does not exist, "does it still reproduce" is really
"**is the requested validation still absent?**". Concretely, the issue reproduces if **all**
of the following hold on the ground-truth build:

1. **The validator never runs `ComputeViewIdState` (or any equivalent recomputation).**
   Corroborated from source: no call to the `DxilComputeViewIdState` pass, to
   `DxilModule::ComputeSerializedViewIdStateForModule`, or to any recomputation of the view ID
   state, reachable from the validation entry points
   (`ValidateDxilModule` / `ValidateDxilContainer` / `DXC_E_*` validation path).
2. **A shader-model-6.1+ module that reads `SV_ViewID` and has *no* `dx.viewIdState`
   metadata node passes validation.** Measured: build such a module (by editing DXC's own
   disassembly and re-assembling it), run the validator over it, and observe success.
3. **The serialized view ID state is not compared against the module.** Measured: leave the
   `dx.viewIdState` node in place but replace its input→output dependency payload with
   all-zeroes (i.e. "this shader has no input→output dependencies" — false for the shader),
   and observe that validation still succeeds. This is claim C: the dependency mapping can be
   wrong/absent and nothing notices.

If instead the validator **rejects** any of (2) or (3) with a diagnostic naming the view ID
state, the request has been implemented in the meantime and the issue does **not** reproduce
(`does-not-repro`, history `fixed`).

## Predicate shape planned

The symptom is that validation **succeeds** on a module that should be rejected. That is an
absence-of-diagnostic finding, so the predicate needs a **positive anchor** proving the probe
actually got as far as validating a real module — otherwise a failed parse, a missing file, or
a tool that never ran satisfies "no error about view ID" for free (SKILL.md: "An
absence-based predicate is satisfied for free by a compile that never got started").

Planned anchors, all of which must appear in the same capture:
- the harness echoes each command it runs, and prints a self-test line proving the *edit it
  claims to have made* is actually present/absent in the module it validated;
- a positive control: the **unmodified** module validates (so the harness can validate at all);
- a negative control: a module corrupted in a way the validator **does** check must be
  **rejected** (so "validation succeeded" is not the harness failing to call the validator).

## Exit-code expectations

A DXIL validation failure exits **E_FAIL (0x80004005)** and is an ordinary diagnosed error —
**not** an internal failure. Do not score it as a crash (SKILL.md exit-code table).

## Repro quality

`prose-only` as filed — the issue contains no shader, no command line and no module. Anything
I build is **agent-constructed** and must be labelled as such.

## History expectation

Not stated in the issue text. If the request is unimplemented the history is
`always-repro'd` (bounded by the v1.4.1907 floor); note that `SV_ViewID` requires shader model
6.1, so any release predating SM 6.1 support would be an `invalid-probe`, and the whole
measurement runs through a harness (assembler + validator), not through a bare `dxc`
invocation, which per SKILL.md means `bisect` must not be used with substituted release
`dxc.exe` binaries.

## What would make this NOT a compiler-measurable question

If it turned out that the only way to observe the gap is through a driver or a runtime, this
would be `not-compiler-verifiable`. It is not: the validator is a compiler-side component and
is reachable from `dxc -Vd`-produced containers plus `dxv`/`IDxcValidator`, so a measurement
exists.
