# 3531 — expected symptom

Issue: "No debug info for locally-declared dynamic resources (SM 6.6)", filed 2021-03-02 by
jeffnn. Label `bug`, milestone `Dormant`, **zero comments**.

Written **before** any compiler was run, per SKILL.md step 2.

## What the issue claims

Given (issue body, verbatim):

```hlsl
static RWByteAddressBuffer DynamicBuffer = ResourceDescriptorHeap[1];
[numthreads(1, 1, 1)]
void DynamicResources()
{
    uint val = DynamicBuffer.Load(0u);
    RWByteAddressBuffer DynamicallyIndexedDynamicBuffer = ResourceDescriptorHeap[256 + val &0xf];
    floatRWUAV[0] = DynamicallyIndexedDynamicBuffer.Load(0);
}
```

> There is no metadata at all for the locally-defined "DynamicallyIndexedDynamicBuffer".

Read together with the title ("No debug info"), the claim is: **a resource declared as a
*local* variable and initialised from `ResourceDescriptorHeap` produces no debug-info metadata
naming that variable**, so a debugger (the reporter works on PIX) cannot present it.

The claim is an **absence**. SKILL.md is explicit that an absence predicate is satisfied for
free by a run that failed for an unrelated reason, and can equally be *falsified* for free.
So the predicate must contain a positive clause that only a successful, debug-info-emitting
compile can satisfy.

## "This reproduces" means

All of the following observed in one run of the repro with `-Zi`:

1. the compile **succeeds** (exit 0) and produces DXIL — no diagnosed error, no crash;
2. debug-info metadata for **ordinary local variables is present in that same run** — i.e.
   the debug-info emitter ran and is capable of naming locals here (self-test clause);
3. and yet **no debug-info metadata entry names `DynamicallyIndexedDynamicBuffer`** — nothing
   of the form `!DILocalVariable(... name: "DynamicallyIndexedDynamicBuffer" ...)`.

"Does not reproduce" = clause 3 fails, i.e. some debug-info entry does name the local
dynamic resource.

## Traps identified up front

- **The name appears in the source, and `-Zi` embeds the source.** DXC records the shader
  text in `!dx.source.contents`, so a bare `not_contains "DynamicallyIndexedDynamicBuffer"`
  is guaranteed false in every run and would report "never reproduced". The absence clause
  must be anchored on the *metadata form* (`!DILocalVariable(...)`), never on the bare name.
- **Compiler Explorer appends `-Zi -Qembed_debug -Fc -` to every DXC pane** regardless of the
  arguments given. For an issue that is entirely about whether debug info is emitted, a CE
  pane can therefore show debug output a plain local run would not. CE is corroboration only;
  the local run decides, and the banner must state what CE adds. The banner must **not** name
  the identifier claimed absent — CE compiles the banner into the source, manufacturing a hit.
- **SM 6.6 did not exist when this was filed** (2021-03-02) and `ResourceDescriptorHeap` is
  SM 6.6-only, so old releases will reject the repro outright. Those are `invalid-probe`s,
  not fixes. A feature-presence control (smallest `ResourceDescriptorHeap` shader, same
  profile/flags) must be run per release to tell "release predates the feature" from
  "something else in my repro was rejected".
- **Both endpoints agreeing is not proof.** The filing date sits inside the release range, so
  a mid-history window is plausible; use `--linear`.
- The repro as filed **does not compile**: `floatRWUAV` is never declared. Any repair is a
  deviation from what was reported and has to be measured, not assumed inert.

## Repro quality

`partial` — the issue supplies real, specific HLSL and names the exact symptom, but the
snippet references an undeclared `floatRWUAV` and gives no command line, target profile or
compiler version. The declaration and the command line are agent-supplied.

## Predicate plan (finalised in `match.json` after exploring real output)

- positive/self-test clause: a `!DILocalVariable` naming a *non-resource* local in the same
  run (`val`), plus evidence the module was produced.
- absence clause: no `!DILocalVariable` naming `DynamicallyIndexedDynamicBuffer`.

## Controls planned

| control | expectation | what it proves |
| --- | --- | --- |
| a shader where a **non-resource** local carries the same name | `no-match` | the absence clause *can* fail; the regex is not simply dead |
| a locally-declared **bound** (non-heap) resource | recorded either way | whether the gap is specific to dynamic resources or covers local resources generally |
| smallest `ResourceDescriptorHeap` shader (feature presence) | per release | separates "release predates SM 6.6" from "this repro was rejected" |
| the shader **as filed** (with a bound `floatRWUAV`) | recorded | measures the deviation my repair introduces |
