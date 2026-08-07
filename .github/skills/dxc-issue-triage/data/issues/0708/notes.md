# Triage — #708 RegisterOffset is being ignored from RegisterAssignment

| | |
| --- | --- |
| Opened | 2017-10-13 (oldest open issue) |
| Labels | `bug` |
| Repro quality | **agent-constructed** (issue was prose-only) |
| Status vs `main` | **repros** |
| History | **always-repro'd** (v1.4.1907 → v1.9.2607) |
| Confidence | **high** — corroborated by source, not just observed output |
| Suggested action | **still-valid-keep-open** (with an open design question) |

## What was tested

The issue gives no shader, only the sentence "if register assignment form with offset is
used, e.g. `register(t1[27])`, the offset will be ignored". Repro constructed from that:

```hlsl
Texture2D tex : register(t1[27]);
float4 main() : SV_Target { return tex.Load(int3(0, 0, 0)); }
```

`dxc -T ps_6_0 -E main repro.hlsl`

## Result

Compiles cleanly (exit 0), no warning, no error. The binding table shows:

```
; tex                               texture     f32          2d      T0             t1     1
```

The resource lands at `t1`; the `[27]` is silently discarded. Identical on every release
from v1.4.1907 (2019-07) through v1.9.2607 (2026-07).

## Corroborating source evidence

This is not just an output observation — the offset is provably dead in the compiler:

- `tools/clang/lib/Parse/ParseDecl.cpp:502` — the offset is parsed and stored into
  `RegisterAssignment::RegisterOffset`.
- `tools/clang/include/clang/AST/HlslTypes.h:269` — the field exists on the AST node.
- `tools/clang/lib/AST/DeclPrinter.cpp:1487` and `ASTDumper.cpp:1070` — it is echoed back
  when printing/dumping the AST.
- `tools/clang/lib/Sema/SemaHLSL.cpp:13166` — it is compared, but only to decide whether two
  register assignments conflict.

There is **no read of `RegisterOffset` anywhere in binding assignment or codegen.** The value
is parsed, stored, printed, and otherwise ignored.

## Assessment

The report is accurate and the bug is live after 8 years. The unambiguous defect is that DXC
**accepts syntax it does not implement and says nothing** — a user writing `register(t1[27])`
gets silently different bindings than they asked for.

What DXC *should* do is a genuine open question: the `register(t<n>[<offset>])` form is not
documented for SRVs, and it is not clear whether the offset should shift the binding, or
whether the syntax should be rejected outright. At minimum a diagnostic is warranted.
@damyanp's 2024 comment ("we should ensure that HLSL 202x does what clang will do in this
case") suggests the semantics decision belongs with the language spec.

**Do not close as stale — it reproduces exactly as reported.**

---

## Shareable repro

<https://godbolt.org/z/MsfE6b1v8> — DXC 1.6.2112 and trunk.

Look at the `Resource Bindings` table in the DXIL output:

    ; tex    texture    f32    2d    T0    t1    1

`HLSL Bind` is `t1` — the `[27]` offset is gone, with no error and no warning. Both compilers
agree, confirming this is long-standing rather than a recent change.
