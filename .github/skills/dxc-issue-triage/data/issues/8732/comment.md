> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#8732](https://github.com/microsoft/DirectXShaderCompiler/issues/8732).

**The lowering this report describes is not on `main` — it belongs to PR #8517.** Checked
against `main` at `ab5400907`
(`dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433`) and against every release
back to v1.4.1907. None of the named symbols exist on `main`: `descriptorHeapImageAliasVars`,
`descriptorHeapBufferAliasVars`, `createDescriptorHeapIndexVar`,
`tryToAssignDescriptorHeap{Image,Buffer}Alias`, `emitDescriptorHeapImageTexelPointer`,
`diagnoseDescriptorHeapAliasMixing`. `main` lowers `ResourceDescriptorHeap[i]` at the point of
use in `SpirvEmitter::doCXXOperatorCallExpr` (`SpirvEmitter.cpp:6642`) and hands back an
ordinary SSA value — there is no per-`VarDecl` alias state to go stale.

**On `main` all five cases fail loudly, and none of them is silent.** Defects 1, 2, 3 and the
undiagnosed heap-only conditional:

```
fatal error: generated SPIR-V is invalid: [VUID-StandaloneSpirv-OpTypeImage-06924]
Cannot store to OpTypeImage, OpTypeSampler, OpTypeSampledImage, or
OpTypeAccelerationStructureKHR objects
  OpStore %29 %30
```

and defect 4: `error: UAV support not implemented with non-emulated heaps.` No crash or
assert on a Debug build, so the "or ICE" half of the title is not observable here either.

The VUID-06924 failure is **not** about mixing: `Interlocked*` needs `OpImageTexelPointer`,
which needs a pointer to an image *variable*, so `main` stores the heap handle into a
`Function` image variable — illegal, and un-promotable by `mem2reg` precisely because
`OpImageTexelPointer` takes its address. A control with no bound resource at all fails
identically. `Interlocked*` on a heap-loaded texture is simply unsupported on `main`.

**`main` is not miscompiling underneath the validator.** Re-run with `-Vd`, the module is what
the source asked for — both descriptors stored into the same variable, last store wins, and
`%boundTex` still present and still in `OpEntryPoint`:

```
     %29 = OpVariable %_ptr_Function_type_2d_image Function
     %30 = OpLoad %type_2d_image %boundTex
           OpStore %29 %30
     %36 = OpUntypedAccessChainKHR … %resource_heap %uint_1
           OpStore %29 %37
     %40 = OpImageTexelPointer %_ptr_Image_uint %29 %39 %uint_0
     %41 = OpAtomicIAdd %uint %40 %uint_1 %uint_0 %uint_1
```

Illegal, not wrong.

[**Compiler Explorer**](https://godbolt.org/z/bcn4zoTdM) — three panes: DXC 1.9.2607 and
trunk showing the fatal error, and trunk with `-Vd` showing the module above. Read the third
pane, not the first two: a reader who sees only the errors will conclude something different
from what is actually happening.

**History is unmeasurable, and that is not a fix.** All 20 releases from v1.4.1907 to
v1.9.2607 were probed; 19 answer `dxc failed : Unknown argument: '-fspv-use-descriptor-heap'`.
Only v1.9.2607 runs the repro, and it matches `main` exactly, same VUID. One usable data point
is not a history.

**One thing that has changed on `main` since this was filed.** The workaround in the report —
separate variables for bound and heap-loaded resources — compiles cleanly on v1.9.2607 but
now fails on `main`:

```
fatal error: generated SPIR-V is invalid: Array must be explicitly laid out with
ArrayStride or ArrayStrideIdEXT decorations. … in the UniformConstant storage class
  %_runtimearr_type_2d_image = OpTypeRuntimeArray %type_2d_image
```

That is the SPIRV-Tools update in ec2ba18da (→ `1c336172`) newly enforcing explicit layout on
`UniformConstant` arrays, already tracked as #8740. `-fvk-use-scalar-layout` does not help.
While #8740 is open, every shader here that actually indexes `ResourceDescriptorHeap` fails to
validate on `main`, so this issue cannot be re-measured there even after #8517 lands. (A
control with `-fspv-use-descriptor-heap` set but no heap indexing still compiles, exit 0.)

**Suggestions**

- The title and body disagree: the title says "silent miscompilation or ICE", while *Actual
  Behavior* says all four defects are now diagnosed and defect 4 no longer ICEs. Only the
  heap-only conditional assignment is still described as silent. Worth retitling, and worth
  stating up front that this is against #8517's branch — otherwise anyone checking it against
  `main` or a release sees a loud validation error and concludes it cannot be reproduced.
- Consider whether this belongs as review feedback on #8517 rather than as a standalone
  issue, and whether the residual heap-only conditional case — the one part still described as
  undiagnosed, needing dataflow analysis rather than the per-variable state check — should be
  tracked on its own.
- Labels: add `correctness` (the reported defect is wrong code, and nothing currently records
  that). Note `incorrect-code` is about *handling* invalid input and does not apply. No
  removals proposed; there may be history here that this triage cannot see.

The report's own analysis held up where it could be checked here: the call sites, the
per-resource-class consumption points, and the aside that an `OpPhi` of image type fails
independently of descriptor heaps — that last one reproduces with a conditional between two
bound textures and no heap flag: `fatal error: generated SPIR-V is invalid: Result type cannot
be OpTypeImage`. The reported defect itself could not be checked, since it is not reachable
from a build of `main`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
