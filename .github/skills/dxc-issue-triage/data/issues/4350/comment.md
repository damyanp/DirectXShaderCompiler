> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4350](https://github.com/microsoft/DirectXShaderCompiler/issues/4350).

Still reproduces on `main` (1.9.0.5433, `13730886e`), and on **every one of the 20 stable
releases** back to v1.4.1907 (2019-07), the oldest release tested that ships a usable `dxc`.
The repro is the issue body unchanged.

```
dxc -T vs_6_0 repro.hlsl
  -> error: llvm::cast<X>() argument of incompatible type!
  -> exit 0x80004005 (E_FAIL)
```

**Where it fails.** The front end accepts the write. Under `-fcgl`, which stops before DXIL
lowering, the compile succeeds and emits a store into the constant buffer (abridged — `!dbg`
metadata and mangled type suffixes elided):

```llvm
; in main
@"$Globals" = external constant %"$Globals"
%2 = call %"$Globals"* @"dx.hl.subscript.cb.rn…"(i32 6, %dx.types.Handle %1, i32 0)
%3 = getelementptr inbounds %"$Globals", %"$Globals"* %2, i32 0, i32 0
call void @"\01?Set@MyStruct@@QAAXXZ"(%struct.MyStruct* dereferenceable(4) %3)

; in Set
%Idx = getelementptr inbounds %struct.MyStruct, %struct.MyStruct* %this, i32 0, i32 0
store i32 1, i32* %Idx, align 4
```

Lowering then walks the users of that cbuffer address and hits
`cast<GetElementPtrInst>(user)` at `lib/HLSL/HLOperationLower.cpp:8847`, under the comment
`// Must be GEP here`:

```
llvm::cast<llvm::GetElementPtrInst,llvm::Instruction>
`anonymous namespace'::TranslateCBAddressUserLegacy
`anonymous namespace'::TranslateCBGepLegacy
`anonymous namespace'::TranslateCBAddressUserLegacy
`anonymous namespace'::TranslateCBOperationsLegacy
TranslateHLSubscript
```

**The const violation is never diagnosed, and that is separable from the crash.** The same
call on a `const` **local** object compiles to exit 0 with no diagnostic and no warning — a
local is an alloca, so the undiagnosed store is representable and lowering has nothing to
choke on. Making `Obj` `static` also compiles cleanly. The internal error needs the object to
be `$Globals`-backed; the missing check does not.

**The crash has four different signatures**, which matters for anyone re-testing this:

| releases | exit | stderr |
| --- | --- | --- |
| v1.4.1907, v1.5.2010 | `0xC0000005` | *empty* |
| v1.6.2104 | `0xC0000005` | `Internal compiler error: access violation…` |
| v1.6.2106, v1.6.2112 | `0x80AA001D` | `Internal Compiler error: llvm::cast<X>() argument of incompatible type!` |
| v1.7.2207 … v1.9.2607, `main` | `0x80004005` | `error: llvm::cast<X>() argument of incompatible type!` |

Matching on the message text reports a regression at v1.6.2106. Matching only the known
internal-failure status set, without text markers, reports it fixed at v1.7.2207. Bare
nonzero exit happens to classify all probe releases correctly, but it also fires on the
ordinary syntax-error control, which returns the same `0x80004005`. None is a valid account
of the history — the repro has failed internally on every release tested.

[Compiler Explorer, four panes](https://godbolt.org/z/TEcGjnve7). Both DXC panes fail
internally. `hlsl_clang_trunk` instead diagnoses it:

```
error: 'this' argument to member function 'Set' has type 'const MyStruct',
       but function is not marked const
note: 'Set' declared here
```

The fourth pane is the control for that: same compiler, same source, `-DCONTROL_MUTABLE` makes
the object `static`, and it compiles (exit 0). So this is a real diagnosis of the construct,
not Clang failing on the shader. This bears on the 2024-07-24 comment about overload resolution
not handling const-ness of the implicit object — the Clang-based front end does handle it
today. Whether that settles the design question in
[hlsl-specs 0007](https://github.com/microsoft/hlsl-specs/blob/main/proposals/0007-const-instance-methods.md)
is a language decision, not something this triage can answer.

**Labels**: suggest adding `crash` (every release fails internally, three with an access
violation, so `bug` alone understates it) and `incorrect-code` (the input is invalid HLSL and
its handling is the defect). `bug` and `hlsl-next` look right as they are.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
