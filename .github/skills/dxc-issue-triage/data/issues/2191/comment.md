> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#2191](https://github.com/microsoft/DirectXShaderCompiler/issues/2191).

**Still reproduces** on `main` (`1.9.0.15422 (main, eff900d54)`), Debug build, with the repro
exactly as filed:

```
$ dxc -T cs_6_0 -E main repro.hlsl
Internal compiler error: LLVM Assert          # exit 0xE0000001
```

The message only reaches `OutputDebugString`, so under a debugger:

```
assert(MaybeODRUseExprs.empty() && "Leftover expressions for odr-use checking")
tools\clang\lib\Sema\SemaDecl.cpp(11156)   in clang::Sema::ActOnFinishFunctionBody
```

Three things the original report does not say:

**It is not specific to `[numthreads]`.** `[maxvertexcount]` on an empty-bodied geometry
shader trips the same assert:

```hlsl
static const uint three = 3;
struct GSOut { float4 pos : SV_Position; };
[maxvertexcount(three)]
void main(inout TriangleStream<GSOut> s) {}     // -T gs_6_0 -E main -> same assert
```

Both go through `ValidateAttributeIntArg` (`SemaHLSL.cpp:13858`), which resolves an
identifier argument by looking up the `VarDecl` and folding its initialiser; 28 attributes
route through it in total.

**The empty body is load-bearing.** Any statement in the body suppresses the assert — the
body does not have to mention the constant, so this is not about the constant being
odr-used:

```hlsl
static const uint eight = 8;
RWBuffer<uint> buf;
[numthreads(eight, 8, 1)]
void main() { buf[0] = 1; }                     // compiles clean
```

(`variant-body-no-const.hlsl`; `variant-odr-used.hlsl`, which does reference `eight`, is
also clean.) That points at the full-expression cleanup rather than the attribute: an
empty body reaches `ActOnFinishFunctionBody` with nothing having drained the entries
`ValidateAttributeIntArg` left in `MaybeODRUseExprs`. Adding a statement is a workaround,
but not a targeted one.

**No shipped compiler is affected.** All 20 releases from v1.4.1907 (2019-07) to v1.9.2607
compile the repro successfully, with the right thread-group size in the DXIL
(`!{i32 8, i32 8, i32 1}`; from v1.7.2207 also `; NumThreads=(8,8,1)`), because release builds
have asserts compiled out (`assert.h`: `#ifdef NDEBUG` → `((void)0)`) and the leftover
bookkeeping is harmless to codegen. So the bisection is silent here by construction, not
because anything was fixed — the assert path and `ValidateAttributeIntArg`'s identifier
branch are unchanged since the first public commit in 2016.

[Compiler Explorer](https://godbolt.org/z/dGK17oobT) shows the Release side: `dxc_1_6_2112`
and `dxc_trunk` both succeed, and so does `hlsl_clang_assertions_trunk` — an assertions build
of the successor HLSL front end — emitting metadata identical to a literal `[numthreads(8,8,1)]`
control. CE carries no assertions-enabled DXC, so it cannot show this issue's symptom.

Two side notes on the linked threads: the rejection reported in #4032 ("compiler emits error
message and rejects input") does not reproduce on any release for this construct — DXC has
accepted a `static const uint` here for as long as is checkable. **#2188 is a different
defect in the same function**: it passes a *component of a const vector* (`c2Thread.x`),
which fails `isCXX11ConstantExpr` outright and is diagnosed; the scalar case here passes
that check and then leaves the odr-use bookkeeping behind. Fixing one will not fix the
other.

Suggested label: add **`crash`** — the issue is currently only `bug`, and this is an assert.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
