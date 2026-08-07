# #2923 — what "this reproduces" means

Written **before** anything was run, from the issue text and from reading the
sources the issue names.

## What the issue says

> Repro: edit the `PixStructAnnotation_SequentialFloatN` case in DXCompiler's
> `pixtest.cpp` to pass the payload struct to a subroutine, and have the
> subroutine call `DispatchMesh`, then run the unit test.
>
> Not clear yet what set of structs are affected. Certainly there are structs in
> the wild that don't show this problem — could be something to do with the fact
> that those shaders were compiled with older dxc, or something to do with the
> structs themselves.

Filed 2020-05-27 by @jeffnn (PIX). Title: *"Structs passed to subroutines (can)
cause the numbering pass to get confused about offsets of members"*. One comment,
from @damyanp on 2024-06-27: *"@jeffnn - is this something we still need to
track?"* — never answered. No labels, no milestone, assigned to @jeffnn.

## What the named test actually does

`PixStructAnnotation_SequentialFloatN` now lives in
`tools/clang/unittests/HLSL/PixTest.cpp:1885` (the file was renamed from
`pixtest.cpp`). Its shader is:

```hlsl
struct smallPayload { float3 color; float3 dir; };
[numthreads(1, 1, 1)]
void main() {
    smallPayload p;
    p.color = float3(1,2,3);
    p.dir   = float3(4,5,6);
    DispatchMesh(1, 1, 1, p);
}
```

`TestStructAnnotationCase` (PixTest.cpp:1229) compiles it as `as_6_5` with
`{-Od | -O1} -HV 2018 -enable-16bit-types`, takes the `DFCC_ShaderDebugInfoDXIL`
(`ILDB`) module out of the container, and runs the two PIX passes
(`PixTestUtils.cpp:244`):

```
-opt-mod-passes -dxil-dbg-value-to-dbg-declare -dxil-annotate-with-virtual-regs
```

"The numbering pass" in the issue title is
`-dxil-annotate-with-virtual-regs` (`lib/DxilPIXPasses/DxilAnnotateWithVirtualRegister.cpp`).
It attaches two pieces of metadata that the issue is about:

* on the payload alloca — `!pix-alloca-reg = !{i32 <base>, i32 <count>}`,
  where `<count>` must be the number of **scalar leaf members** of the struct
  (`CountStructMembers`, which recurses through structs/arrays/vectors);
* on each store into a member — `!pix-alloca-reg-write = !{i32 <base>,
  i32 <size>, i32 <memberOffset>}`, where `<memberOffset>` is the index of that
  scalar member within the alloca's register run.

PIX uses those to attribute a store to the right member when stepping a shader.
The test checks exactly that: `ValidateAllocaWrite` (PixTest.cpp:1373) asserts
`regBase + index == i` for the *i*-th recorded store, and the body of the test
asserts six stores named `color.x, color.y, color.z, dir.x, dir.y, dir.z` and a
six-member alloca.

## The repro to build

The same shader, but with the payload passed to a subroutine that calls
`DispatchMesh`:

```hlsl
struct smallPayload { float3 color; float3 dir; };
void Sub(smallPayload p) { DispatchMesh(1, 1, 1, p); }
[numthreads(1, 1, 1)]
void main() {
    smallPayload p;
    p.color = float3(1,2,3);
    p.dir   = float3(4,5,6);
    Sub(p);
}
```

Same profile and flags as the test (`-T as_6_5 -E main -Od -HV 2018
-enable-16bit-types`), same two passes.

## "Reproduces" =

After `-dxil-dbg-value-to-dbg-declare -dxil-annotate-with-virtual-regs`, the
numbering of the payload struct's members is **wrong**: at least one of

1. the payload alloca's `!pix-alloca-reg` count is not the number of scalar leaf
   members of `smallPayload` (6); and/or
2. the six member stores do not carry `!pix-alloca-reg-write` offsets that form
   the distinct run 0,1,2,3,4,5 relative to the alloca base — e.g. duplicated
   offsets, or offsets past the end of the alloca's register run; and/or
3. the pass fails outright (assert / crash) on the input.

Any of those is "the numbering pass got confused about offsets of members" and
would fail the assertions in `PixStructAnnotation_SequentialFloatN`.

## "Does not reproduce" =

The subroutine version numbers the six members exactly as the non-subroutine
version does: a six-register alloca whose six member stores carry offsets
0..5, one each. That is the control — the unmodified test shader must produce
that, or the measurement is meaningless.

## Repro quality

**`prose-only` as filed** — the issue supplies no shader, no command line and no
output; it names a unit-test case and describes an edit to make to it. The repro
used here is **agent-constructed** from that description plus the named test's
own source.

## Known hazards for this issue

* The symptom is invisible to `dxc` alone. `-dxil-annotate-with-virtual-regs`
  is a PIX-only pass that never runs during ordinary compilation, so a plain
  `dxc` invocation cannot show it and a predicate over `dxc` output would score
  every build "clean" for a reason that has nothing to do with the defect.
* `as_6_5` did not exist before v1.5.2010 — v1.4.1907 will be an invalid probe
  for any release history (see #3251, #3259 in this tree, both `as_6_5`).
* The PIX passes live in `dxcompiler.dll`, not in `dxc.exe`, so a release
  history has to drive the release's DLL, not its driver.
