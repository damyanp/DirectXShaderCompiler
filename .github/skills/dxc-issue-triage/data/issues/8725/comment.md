> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#8725](https://github.com/microsoft/DirectXShaderCompiler/issues/8725).

Reproduces on `main` (`1.9.0.5433`, `13730886e`), exactly as reported, and on every
release that can compile the shader at all. Compiler Explorer, annotated:
<https://godbolt.org/z/Eo8YbKs5n>

**The assert.** `-T lib_6_9` on the repro exits `0xE0000001`. The first assert to fire is the
one you noted as "preceding" — it is the primary failure, not a side effect:

```
Error: assert(type->isReferenceType() == E->isGLValue() && "reference binding to unmaterialized r-value!")
File:  tools/clang/lib/CodeGen/CGCall.cpp(2962)
Func:  clang::CodeGen::CodeGenFunction::EmitCallArg
```

`CGMSHLSLRuntime::EmitHLSLOutParamConversionInit` (`CGHLSLMS.cpp:6185`) inserts a
copy-in/copy-out temporary for `Invoke`'s `inout` payload, then rewrites the argument to a
`DeclRefExpr` built with **`VK_RValue`** because the payload is an aggregate
(`CGHLSLMS.cpp:6384-6392`, "Aggregate type will be indirect param convert to pointer type. So
don't update to ReferenceType, use RValue for it."). `EmitCallArg` then sees `type` =
`Payload &` from the callee prototype against a non-glvalue expression, and the assert at
`CGCall.cpp:2962` is precisely that mismatch. Continuing past it lands in the by-value
aggregate path — `CreateLoad` at `CGCall.cpp:3411`, `CreateBitCast` at `CGCall.cpp:3429` —
which is where your `"Invalid cast!"` comes from.

**The emitted IR, which makes the release-build face self-explanatory.** `-fcgl` succeeds and
prints:

```llvm
%14 = load %struct.Payload, %struct.Payload* %2
%15 = bitcast %struct.Payload %14 to %struct.Payload*
call void @"dx.hl.op..void (i32, %dx.types.HitObject*, %struct.Payload*)"(
    i32 382, %dx.types.HitObject* %obj, %struct.Payload* %15)
```

A struct value bitcast to a pointer. With `inout` the parameter lowers to
`%struct.Payload* noalias %p`, `SafeToSkip` holds (`CGHLSLMS.cpp:6355`), no temporary is
created and the pointer is passed straight through — which is why the workaround works. A
plain local payload passed straight to `Invoke` takes the same path via the alloca case
(`CGHLSLMS.cpp:6347`), which is why SER is not broken for everyone.

**Why plain `TraceRay` is fine — a Sema asymmetry, and this is the actionable part.** Not the
intrinsic table: `gen_intrin_main.txt` says `inout udt Payload` for the free function
`TraceRay` (:311), for `Invoke` (:1141) and for `HitObject::TraceRay` (:1140) alike. The
difference is in the two functions that build intrinsic declarations:

- `AddHLSLIntrinsicFunction` (`SemaHLSL.cpp:2102`), for free functions, makes an `out`/`inout`
  parameter an lvalue reference only if it is **neither an array nor a record type**, or is a
  vector/matrix (`SemaHLSL.cpp:2123-2135`) — *"Aggregate type will be indirect param convert to
  pointer type. Don't need add reference for it."* `Payload` is a plain record, so
  `TraceRay`'s payload stays `Payload`.
- `AddHLSLIntrinsicMethod` (`SemaHLSL.cpp:6296`), for object/class methods, makes **every**
  `out`/`inout` parameter an lvalue reference (`SemaHLSL.cpp:6334-6340`), with no such guard.
  `dx::HitObject::Invoke` is a `[[static,class_prefix]]` method, so its payload is `Payload &`.

That is precisely the term the assert tests:

```
TraceRay   type = Payload     ->  isReferenceType() false == isGLValue() false   holds
Invoke     type = Payload &   ->  isReferenceType() true  != isGLValue() false   asserts
```

`-fcgl` bears it out: the `TraceRay` case builds the same copy-in/copy-out temporary but passes
its **address**, while the `Invoke` case materialises a second aggregate temp and then loads and
bitcasts it. So the temporary alone is not the defect — **it takes the temporary and a
reference-typed parameter together**, and each clean spelling is missing exactly one of the two.

**The title understates the scope.** Two variants fail identically, with the same assert at the
same line:

- `dx::HitObject::TraceRay(RTAS, …, ray, p)` with the same by-value `p`. Not `Invoke`-only.
- A mutable `static Payload g` passed straight to `Invoke` from the entry point — **no by-value
  parameter and no user function involved.** A mutable global is not an alloca, not
  groupshared and not a `noalias` argument, so it takes the same copy-in path.

So the trigger is broader than "passed by value": what both failing cases have in common is an
object-method intrinsic with an `inout` record parameter, called with an argument whose address
is not provably non-aliasing. `Invoke` and `HitObject::TraceRay` are the two that were measured;
other object methods built by the same path were not enumerated. Your other two observations
both check out: plain `TraceRay` with a by-value payload compiles clean (exit 0,
for the Sema reason above), and `-disable-payload-qualifiers` with no `[raypayload]`
annotations still asserts.

**History.** v1.8.2505 is the first release that can express this at all; every
release from v1.8.2505 through v1.9.2607 shows the release-build face verbatim
(`Instructions must be of an allowed type` at an `unreachable`). All 15 older releases answer
`error: invalid profile lib_6_9` — feature absence, not a clean run; v1.4.1907 and v1.8.2502
reject a trivial `lib_6_9` shader containing no SER at all in the same way. There is no window
to bisect.

**On the fix.** Your reading of the
existing guard is right: for `out`/`inout`/`ref` intrinsic parameters,
`HLSLExternalSource::MatchArguments` (`SemaHLSL.cpp:7093`) rejects only `pType.isConstant()` or
an `OK_BitField` argument — an `in` parameter is neither, and neither is a mutable global.
Separately, giving `AddHLSLIntrinsicMethod` the same record-type guard `AddHLSLIntrinsicFunction`
has would stop the assert, but on its own it would make the by-value case compile *silently*,
writing the payload back into a copy the caller never sees. Which of those to do, and whether
the static-global case should be diagnosed at all or simply lowered correctly, is a language
decision rather than something this triage can settle.

Label suggestion: add `crash` (it is an assert/ICE, so `bug` alone understates it),
`incorrect-code` (invalid input DXC fails to diagnose), `diagnostic` (the ask is a Sema error),
`sm6.9`; remove `needs-triage`. Not proposing `correctness` — the correct outcome is rejection,
not different codegen. We may be missing history behind the current labels.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please flag
anything that looks wrong.</sub>
