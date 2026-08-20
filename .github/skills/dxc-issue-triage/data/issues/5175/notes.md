# #5175 -- IDxcCursor does not support template parameter and template argument querying

## What was tested

This is an API-surface feature request, not a code-generation question: the reported gap is on
`IDxcCursor` (`include/dxc/dxcisense.h`), the COM interface DXC's own intellisense tooling
exposes, and there is no `dxc.exe` command line that walks or dumps cursors (confirmed:
`dxc --help` has no AST/cursor/intellisense-dump flag; see `source-evidence.txt` intro and
`expected.md`). Per SKILL.md's guidance for capability-absence claims ("inspect the public
intrinsic/interface table and all emitters" before relying on a single probe), the primary
evidence here is source inspection of the interface and its implementation, at ground truth
`main-debug`, whose source tree is confirmed equal to public upstream
`89e2f98e29c289ae8ad9e00dd310104fea9fd7df` outside this skill directory
(`version-verification.txt`).

Full detail and every quoted excerpt is in `source-evidence.txt`. Summary:

1. **`IDxcCursor` has no template-argument accessors.** It has cursor *kinds* for templates
   (`DxcCursor_ClassTemplate`, `DxcCursor_TemplateRef`, etc.) but the only per-argument
   accessors are `GetNumArguments`/`GetArgumentAt`, which are generic function-call-argument
   accessors (see #3), and `GetQualifiedName(BOOL includeTemplateArgs, ...)`, whose flag only
   controls whether a rendered *string* includes template arguments as text.
2. **No accessor returns structured template-argument data.** A caller cannot get an argument
   count, per-argument kind, or per-argument value/type -- only a formatted name string
   (`"Foo<float, -2, 3>"`) that would have to be parsed, which is exactly what the reporter's
   AST dump shows is otherwise unrecoverable (the `float` type argument has no cursor at all;
   the `-2`/`3` values appear only as unrelated child expression cursors under the
   `DxcCursor_TemplateRef`).
3. **`IDxcCursor::GetNumArguments`/`GetArgumentAt` are thin wrappers around libclang's generic
   `clang_Cursor_getNumArguments`/`clang_Cursor_getArgument`.** This confirms the reporter's own
   framing ("I made a modest attempt at porting these changes"): the fix pattern is exactly the
   same shape as these two methods, forwarding to the template-argument equivalents.
4. **The underlying `clang_Cursor_getNumTemplateArguments`/`getTemplateArgumentKind`/
   `getTemplateArgumentValue`/`getTemplateArgumentUnsignedValue` already exist in this
   repository's libclang fork** (`tools/clang/tools/libclang/CXCursor.cpp`, exported in
   `libclang.exports`) -- but every one of them is gated on
   `clang_getCursorKind(C) == CXCursor_FunctionDecl` and reached only through
   `FunctionDecl::getTemplateSpecializationInfo()`. This is precisely the **pre-September-2022**
   upstream `libclang` behaviour (function templates only) that the issue's own linked change,
   https://reviews.llvm.org/D134416, superseded upstream by extending the family to class
   templates and partial specializations. `git log --oneline --all -- tools/clang/tools/
   libclang/CXCursor.cpp` shows only 4 commits ever touched this file, and none of them (back to
   the original 2016 clang import) added template-argument handling of any kind. So even a
   straightforward port of the pattern in #3 to add matching `IDxcCursor` methods would still
   return `-1`/`Invalid` for a `DxcCursor_ClassTemplate`/`_TemplateRef` cursor like the
   reporter's `Foo`/`Foo<float, -2, 3>` -- the class-template extension itself was never
   backported, only the function-template-only precursor exists here.
5. **`IDxcCursor`'s entire history never added template-argument querying.**
   `git log --oneline --all -- include/dxc/dxcisense.h` lists every commit that ever touched
   the header, from the original 2016 import through the most recent (2025-06-03, an unrelated
   raytracing/work-graphs change); every one is a portability, licensing, formatting, or
   unrelated-API-addition change (code completion, presumed source location). This establishes
   `always-repro'd`: the gap has existed, unchanged, since the interface's introduction and
   still exists at HEAD/`89e2f98e29c289ae8ad9e00dd310104fea9fd7df`.
6. **No test coverage exists for template-argument cursor querying**
   (`tools/clang/unittests/HLSL/DXIsenseTest.cpp` has zero occurrences of "Template"),
   consistent with (though not independent proof of) the feature never having been added.

**Anti-vacuity control:** the reporter's exact repro (`repro.hlsl`, verbatim from the issue) is
valid HLSL and compiles cleanly at exit 0 on ground-truth `main-debug`
(`variant-valid-template-source-main-debug.txt`, captured via
`triage.py run --shader repro.hlsl --args "-T lib_6_3 -HV 2021 repro.hlsl" --label
valid-template-source --expect no-match`; unscored, since no `match.json` exists for this
issue -- see below). This rules out the alternative explanation that the interface gap is moot
because the input itself no longer compiles.

No `cmd.txt`/`match.json` were created: there is no compiler diagnostic or codegen artifact
that observes an *absent COM method*, so a predicate over compiler output would be hollow
(SKILL.md: "match.json and cmd.txt may be deliberately absent when compiler output cannot
answer the question"). `bisect` is not applicable for the same reason -- there is nothing a
release's `dxc.exe` can be asked to do that exercises `IDxcCursor` at all.

Compiler Explorer was deliberately skipped (`godbolt --skip`, recorded in
`.cache/triage.db`'s `godbolt_skip` column and echoed in `verdict.json`): CE compiles source and
shows diagnostic/IR panes, it has no surface for walking an intellisense cursor tree, so a link
would show only that `repro.hlsl` compiles cleanly -- already covered by the anti-vacuity
control above -- and would not show the reported gap.

## Assessment

The issue is exactly what it says: `IDxcCursor` genuinely has no way to enumerate or inspect
template arguments, for any template kind. The maintainer's 2023-07-13 comment (`llvm-beanz`)
set expectations that this would not be prioritized, citing a long-term move away from
`IDxcCursor` toward LSP-based tooling, while explicitly saying patches would be accepted. Source
evidence here confirms the fix would be small and precedented on the `IDxcCursor` side (mirror
`GetNumArguments`/`GetArgumentAt`), but incomplete without also porting D134416's class-template
extension into `CXCursor.cpp`, since the currently-vendored `clang_Cursor_getTemplateArgument*`
family only recognizes `FunctionDecl`.

No part of the issue's text is stale: the title, body and the reporter's own comment describing
the AST dump all still match current behaviour, and the maintainer's comment (which sets
expectations rather than asserting a technical fact) has not become inaccurate either.

Sampling note: this is a single feature-request issue, not a crash/regression; its verdict
process (source inspection, no release bisection) does not generalize to code-generation issues
in the same batch.
