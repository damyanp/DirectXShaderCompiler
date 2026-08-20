> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5173](https://github.com/microsoft/DirectXShaderCompiler/issues/5173).

Still reproduces on `main` (commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`,
built Debug).

Confirmed with a small standalone harness that loads `dxcompiler.dll` and
drives `IDxcIntelliSense`/`IDxcTranslationUnit`/`IDxcCursor` directly on a
shader with a semantic on a struct field, a function parameter, and the
return type (`SV_POSITION`, `TEXCOORD0`, `NORMAL0`, `SV_TARGET`). The parsed
cursor tree contains **no attribute-kind cursor at all** for any of the
three — not even the generic `DxcCursor_UnexposedAttr` an ordinary
unrecognised Clang attribute would produce. A control shader with a real
`[numthreads(...)]` attribute alongside a semantic on the same function
confirms the harness does surface an attribute cursor (`UnexposedAttr`) when
one genuinely exists; only the semantic side is silent. Same result on the
oldest and newest catalogued release builds (v1.4.1907, v1.9.2607) as on
`main`, and `git log` shows no commit has ever touched libclang's
`CXCursorKind` mapping for an HLSL attribute — this has been the case for as
long as the behavior is checkable.

Source explains why: `HLSLSemantic` is declared in `Attr.td`, but nothing in
the compiler ever constructs an `HLSLSemanticAttr` — semantics are recorded
through a separate mechanism, `hlsl::UnusualAnnotation`/`SemanticDecl`
(`Decl::getUnusualAnnotations()`), which is never visited by libclang's
`CursorVisitor::VisitAttributes` (it only walks `Decl::attrs()`). So this
isn't an attribute that libclang exposes generically and DXC never
special-cased — it's a side-channel `IDxcCursor` structurally cannot reach
at all.

Given the existing reply that this area is deprioritized in favor of LSP
tooling, suggesting `enhancement-not-bug` rather than a bug label — the
compiler isn't misbehaving; the interface was never extended for this.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
