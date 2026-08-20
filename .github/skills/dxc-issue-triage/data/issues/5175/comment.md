> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5175](https://github.com/microsoft/DirectXShaderCompiler/issues/5175).

Confirmed still missing on current `main` (`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`):
`IDxcCursor` (`include/dxc/dxcisense.h`) has template cursor kinds but no
`GetNumTemplateArguments`/`GetTemplateArgumentKind`/`GetTemplateArgumentValue`-style methods.
The only argument accessors, `GetNumArguments`/`GetArgumentAt`, forward to libclang's generic
`clang_Cursor_getNumArguments`/`clang_Cursor_getArgument`; no template-specific equivalents are
wired.

The underlying `clang_Cursor_getNumTemplateArguments` family already exists in this repo's
libclang fork (`tools/clang/tools/libclang/CXCursor.cpp`, exported in `libclang.exports`) but is
still pre-D134416, gated on `clang_getCursorKind(C) == CXCursor_FunctionDecl` via
`FunctionDecl::getTemplateSpecializationInfo()`. Only 4 commits have touched that file, and none
add template-argument handling. Without porting D134416's class-template/partial-specialization
extension into `CXCursor.cpp`, wiring `IDxcCursor` alone would still return `-1`/`Invalid` for a
class-template cursor such as `Foo<float, -2, 3>`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
