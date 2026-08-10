> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2923](https://github.com/microsoft/DirectXShaderCompiler/issues/2923).

@damyanp — yes, **this still misbehaves on `main`** (`1.9.0.5433`, `13730886e`).

No modified unit test is needed: `repro.hlsl` is
`PixStructAnnotation_SequentialFloatN`'s shader with the edit the issue asks
for:

```hlsl
struct smallPayload { float3 color; float3 dir; };
void Sub(smallPayload p) { DispatchMesh(1, 1, 1, p); }
[numthreads(1, 1, 1)] void main() {
  smallPayload p;
  p.color = float3(1, 2, 3);
  p.dir = float3(4, 5, 6);
  Sub(p);
}
```

```
dxc   -T as_6_5 -E main -Od -HV 2018 -enable-16bit-types -Zi -Qembed_debug repro.hlsl -Forepro.dxo
dxa   -extractpart=dbgmodule -o=repro.ildb.bc repro.dxo
dxopt -o=repro.bc repro.ildb.bc -opt-mod-passes -dxil-dbg-value-to-dbg-declare -dxil-annotate-with-virtual-regs
opt   -S -o=repro.ll repro.bc
```

In the resulting module, `main`'s own local `p` (`DW_TAG_auto_variable`, source
line 19) is described member-by-member by PIX virtual registers 0..5 — and none
of them is ever written. All six member writes were numbered onto registers
6..11, which belong to the inlined subroutine's parameter copy
(`DW_TAG_arg_variable`, source line 16):

```
%0..%5   [1 x float]              regs[0]..regs[5]
         declares: p [DW_TAG_auto_variable src-line 19] !DIExpression(DW_OP_bit_piece, 0|32|64|96|128|160, 32)
         writes  -> registers: (none)

%6       %struct.smallPayload.0   !pix-alloca-reg !{i32 1, i32 6, i32 6}
         declares: p [DW_TAG_arg_variable src-line 16] !DIExpression()
         writes  -> registers: 6,7,8,9,10,11
```

`ValidateAllocaWrite` computes `regBase + index`, so the modified test fails
with `0 != 6` for `color.x` (and 1..5 likewise). The same happens at `-O1`:
there `main`'s `p` holds registers 6..11 and the callee's copy holds 0..5, but
it is again the **caller's** variable that receives no writes.

Two controls, same pipeline: the unmodified test shader is numbered correctly
(one variable, registers 0..5, all written), and so is the same repro with the
subroutine taking the payload **`inout`**. Here the by-value struct copy is the
trigger, not the subroutine call.

**What has changed since 2020.** Running each release's own `dxc.exe` and its
own `dxcompiler.dll` (via `dxopt -external`) over 22 builds:

| | v1.5.2003 … v1.6.2104 | v1.6.2106 … v1.9.2607, main |
| --- | --- | --- |
| `repro.hlsl` | numbered correctly | caller's `p` unwritten |

The IR shape is the same on both sides of that line — the same six
`DW_OP_bit_piece` shadow allocas for `main`'s `p`. At v1.6.2104 they each carry
a write:

```
  %1     [1 x float]   regs[0]  declares: p [DW_TAG_auto_variable src-line 19]
         writes  -> registers: 0            <-- v1.6.2104
         writes  -> registers: (none)       <-- v1.6.2106 onwards
```

Cross-probing {dxc 2104, dxc 2106} × {passes 2104, passes 2106} shows the
result follows the **pass DLL**, not the compiler, so the change is in
`lib/DxilPIXPasses` rather than in the debug info `dxc` emits. Nine commits
touch that directory in the window, five of them `DxilDbgValueToDbgDeclare.cpp`
(`git log v1.6.2104..v1.6.2106 -- lib/DxilPIXPasses/`); release-to-release
probing cannot tell them apart, so no commit is named here.

Caveat: at v1.5.2003 (2020-03-25), the release current when this was filed,
`repro.hlsl` is numbered perfectly. Since the issue says *"Not clear yet what
set of structs are affected"*, this repro is a reconstruction from the described
edit and may not be the instance seen in 2020 — but it is the same scenario, and
it is broken today.

No Compiler Explorer link: CE runs `dxc` only, and this shader compiles cleanly
there — the symptom is entirely in metadata the PIX passes add afterwards.

Suggested labels: `PIX`, `debug info` (the bad metadata is derived from
`llvm.dbg.value` by `DxilDbgValueToDbgDeclare`), and `bug`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
