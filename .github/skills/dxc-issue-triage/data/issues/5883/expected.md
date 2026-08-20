# Expected symptom — #5883

Reported: initializing a **const-qualified** local variable of a struct/array
type whose (transitive) field is written from a **variable that was mutated
after its own declaration** produces DXIL that stores the variable's
*declaration-time* values, silently discarding the runtime writes made before
the const-qualified init. A non-const instance of the same struct correctly
captures the post-mutation values.

Concretely, for:

```hlsl
struct S { float2x3 m; };
...
float2x3 m = float2x3(42,43,44,45,46,47);
m[0] = float3(1,2,3);
m[1] = float3(4,5,6);
const S a = {m};              // BUG: should capture {1,2,3,4,5,6}
buffer.Store3(0u,  int3(a.m[0]));
buffer.Store3(16u, int3(a.m[1]));
```

**Reproduces** when the emitted DXIL's `RawBufferStore` calls carry the
*declaration-time* constants `42,43,44` / `45,46,47` instead of the
post-mutation values `1,2,3` / `4,5,6`.

**Does not reproduce** when the emitted DXIL carries the post-mutation values
(matching the non-const control `S a = {m};`, which the reporter confirms is
correct).

The reporter's own root-cause analysis (2023-10-24 and 2023-10-25 comments)
traces this to `CodeGenFunction::EmitVarDecl`'s HLSL "treat local const as
static global" path, which succeeds in calling
`CGMSHLSLRuntime::EmitHLSLConstInitListExpr` -> `ScanConstInitList` ->
`CodeGenModule::EmitConstantInit(*Var)` on the *declaration* of a mutated
local variable without checking whether the variable was written again
between its declaration and the point it is read into the const init list.
A later (2024-01-26) comment widens the report: the same defect fires for
struct/array of *any* type combination, not only matrices, and states the
reporter's team (Tint) worked around it by no longer emitting `const` locals
at all.

Repro quality: **complete** (the issue body is a standalone, compilable
compute shader; reporter also supplied two Compiler Explorer links with
additional struct/array/vector/matrix combinations).
