# Expected symptom

Reported by @jeremyong on 2023-04-25, labelled `enhancement`.

Upstream `libclang` exposes `clang_Cursor_getNumTemplateArguments`,
`clang_Cursor_getTemplateArgumentKind`, `clang_Cursor_getTemplateArgumentValue` and
`clang_Cursor_getTemplateArgumentUnsignedValue` on `CXCursor`, and since a Sept-2022 upstream
change (https://reviews.llvm.org/D134416) these work for class templates and partial
specializations, not just function templates. DXC's own COM-based intellisense surface,
`IDxcCursor` (`include/dxc/dxcisense.h`), has no equivalent methods at all: there is no way to
enumerate a cursor's template arguments or query their kind/value through `IDxcCursor`.

The reporter dumped the AST for:

```hlsl
template <typename A, int B, uint C> class Foo {};
Foo<float, -2, 3> foo;
```

and found the `Foo` reference cursor is kinded `DxcCursor_TemplateRef`, but the only way to see
the `-2` and `3` arguments is as two unrelated child cursors (`UnaryOperator`/`IntegerLiteral`
and `IntegerLiteral`) with no cursor exposing that they are template arguments, and no way at
all to recover the `float` type argument.

**"Reproduces" means:** `IDxcCursor` (the interface DXC actually ships and that VS/tooling
consumes) still has no `GetNumTemplateArguments`/`GetTemplateArgumentKind`/
`GetTemplateArgumentValue`/`GetTemplateArgumentUnsignedValue`-style methods, i.e. the
capability described in the issue is still absent from the shipped API surface.

**"Does not reproduce" would mean:** `IDxcCursor` (or a documented successor surface) now
exposes an equivalent way to query template arguments.

This is an API-surface absence, not a compile-time code generation question, so there is no
`dxc.exe` command line that observes it directly — `IDxcCursor` is a COM interface consumed
programmatically (e.g. by Visual Studio's HLSL tooling), and `dxc.exe` has no flag that walks
or dumps intellisense cursors. Per the skill's guidance for capability-absence claims, the
primary evidence is inspecting the interface declaration and its implementation, corroborated
by the interface's full commit history.

Repro quality: **complete** — the issue gives the exact input and the exact (formatted) AST
dump the reporter's internal tool produced from it; what cannot be redone without custom
tooling is only the *act* of walking `IDxcCursor` interactively, not the input/output pair
itself.
