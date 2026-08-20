# Expected symptom (written before any probe is run)

Issue #5173: the reporter walks an AST via `IDxcTranslationUnit`/`IDxcCursor` and
observes that the semantic annotations on struct fields, function parameters,
and function return types (e.g. `SV_Target`, `TEXCOORD0`) do not appear
anywhere in the cursor tree. They ask whether a corresponding `CXCursor` kind
could be added, or for guidance on doing so themselves. A maintainer
(llvm-beanz) replied (2023-07-13, ~81 days after the issue was filed on
2023-04-23) that the project is "pretty unlikely to prioritize" this because
the long-term plan is to move away from `IDxcCursor` in favor of upstream LSP
tooling, but that a patch would be accepted.

Correction: an earlier draft of this file mis-stated the comment as arriving
"the same day" the issue was filed; `issue.json`'s timestamps (`createdAt`
2023-04-23T06:55:47Z, comment `createdAt` 2023-07-13T20:30:47Z) show it was
~81 days later. Fixed here as a factual correction of a dating error, not a
redefinition of what "reproduces" means — the symptom criterion below is
unchanged.

This is a feature-request / API-surface issue, not a crash or wrong-codegen
bug. "Reproduces" here means: walking the cursor tree for a declaration that
carries an HLSL semantic (struct field, function parameter, function return
type) exposes no cursor whose *kind* identifies it as a semantic annotation,
and no accessor on that cursor (or on the enclosing declaration cursor)
returns the semantic string (e.g. `"SV_Target"`) through the public
`IDxcCursor` interface. Concretely: the semantic attribute is internally
represented (`HLSLSemanticAttr` in `Attr.td`) and *is* attached to the
Decl, but it is walked through the same generic "attribute" cursor path as
every other Clang attribute (`CursorVisitor::VisitAttributes`), and DXC has
never added an HLSL-specific `DxcCursorKind` for it, so the best a caller can
see is a generic `DxcCursor_UnexposedAttr` child cursor whose `GetSpelling()`
returns an empty string.

"Does not reproduce" would mean a distinguishable cursor kind (or some other
accessor) now surfaces the semantic string.

Repro quality: `agent-constructed`. The issue contains no attached shader or
harness code, only a prose description of the AST-walking behavior and the
API in question; the repro shader and the IDxcIntelliSense-driving harness
below were built to test the described claim, choosing a shader that exposes
all three named surfaces (struct field, function parameter, function return
type).

This is not measurable through `dxc.exe`'s command line: `IDxcCursor` is a
COM/libclang-style AST-walking API, not something a compile invocation prints
to stdout. The measuring instrument is a small standalone harness
(`isense_probe.cpp`) that dynamically loads a given `dxcompiler.dll`
(ground truth or a cataloged release) and drives
`IDxcIntelliSense`/`IDxcIndex`/`IDxcTranslationUnit`/`IDxcCursor` directly,
printing the kind, spelling, and display name of every cursor in the parsed
tree. `cmd.txt`/`match.json` are intentionally absent for this reason; see
`manual-case-*.txt` for the harness invocations and captured output instead.
