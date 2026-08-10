> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4307](https://github.com/microsoft/DirectXShaderCompiler/issues/4307).

Still reproduces exactly as filed on `main` (`13730886e`), and on **every DXC release that has
ever had mesh shaders** — back to v1.5.2010 at `ms_6_5`, and all 18 releases from v1.6.2104 to
v1.9.2607 at `ms_6_6`. On v1.9.2607, dropping `/Od` leaves the same diagnostic.

```
$ dxc repro.hlsl /Zi /E main /Od /Fo test.mso /Tms_6_6 -Qembed_debug
error: validation errors

repro.hlsl:11: error: Function main with parameter is not permitted, it should be inlined.
Validation failed.
```

## DXC already has the diagnostic being asked for

Take the same shader and change line 22 to read the **whole element** instead of one member
(`case-elem-read.hlsl` below is `repro.hlsl` with only that line rewritten, keeping the line
numbering). DXC then produces exactly the shape of message the report asks for, on the line the
report asks for:

```
case-elem-read.hlsl:22:18: error: output arrays of a mesh shader can not be read from
                Vertex _copy = _vertices[ _sv_groupthreadid.x ]; _vertices[ 0 ].m_value = _copy.m_value * sign( toto );
                               ^
```

That is `err_hlsl_load_from_mesh_out_arrays`, emitted from `Sema::DefaultLvalueConversion`
([`SemaExpr.cpp:698`](https://github.com/microsoft/DirectXShaderCompiler/blob/main/tools/clang/lib/Sema/SemaExpr.cpp#L698)):

```cpp
if (isa<ArraySubscriptExpr>(E) && IsExprAccessingMeshOutArray(E)) {
  Diag(E->getExprLoc(), diag::err_hlsl_load_from_mesh_out_arrays);
```

`_vertices[i].m_value` is a `MemberExpr` whose base is the subscript, so `isa<ArraySubscriptExpr>`
is false — and `IsExprAccessingMeshOutArray` handles only `ArraySubscriptExpr`, `ImplicitCastExpr`
and `DeclRefExpr`, with no `MemberExpr` case either. The front end therefore says nothing
(`-fcgl` on the repro exits 0), the read-modify-write on the `out vertices` argument reaches
`LegalizeDxilInputOutputs`, whose `bLoad && bStore` switch has no case for the mesh qualifiers
and falls through without introducing a temporary, and the entry point arrives at the DXIL
validator still carrying a parameter — which is the generic message above, located on the
signature because a whole-module check has no idea about line 22.

So this looks like **extending an existing check to `arr[i].member`**, not adding a new
diagnostic. The diagnostic and its guard both arrived in `968fe4113` ("Add support for HLSL
Meshlets", 2019-07-11), which matches the release history: nothing regressed, the check was
simply never widened.

## Two other things the triage turned up

**A Debug build asserts on this shader**, before the reported message:
`DXASSERT(0, "invalid input qual here")` at `ScalarReplAggregatesHLSL.cpp:6065` in
`LegalizeDxilInputOutputs` — the `default:` arm of that same switch. Release builds compile the
assert out and fall through, which is why the shipped behaviour is a confusing validation error
rather than a diagnostic.

**The last paragraph of the report no longer describes DXC** (and may not have in 2022). Passing
the member to an `out float` parameter compiles **cleanly** on `main` and on all 18 releases;
passing the whole element to an `out Vertex` parameter produces the *good* diagnostic. Only
`inout` — which copies in as well as out, i.e. the same read as line 22 — reproduces the vague
error. Worth ignoring that sentence when scoping a fix.

[Compiler Explorer, dxc 1.6.2112 vs trunk](https://godbolt.org/z/Prfo6ssE7) — same message on
both. Note CE runs Release builds, so it cannot show the assert above; and `clang` there cannot
compile mesh shaders at all yet (`unknown type name 'vertices'`), so there is no successor
comparison to make.

The shader in the 2023 comment behaves identically — v1.9.2607 reports
`comment-repro.hlsl:166: error: Function main with parameter is not permitted, it should be
inlined.`, where line 166 is again the entry signature and the offending `inout` parameters are
at line 133.

**Labels:** keep `diagnostic`; suggest adding `enhancement` (the ask is a better error, not a
behaviour change), `incorrect-code` (this is about how invalid code is reported) and `crash`
(the measured assert above).

---

<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
