# Issue 3708 — what "this reproduces" means

Written **before** any compiler was run, from the issue text and its four comments only.

## What was reported

Title: *Component swizzling / vector indexing not considered a constant expression*
Filed 2021-04-24. Label: `fxc-disagrees`. No maintainer has disputed the report.

Body claim, verbatim:

> This issue manifests when trying to define arrays where the length is a component of a
> constant variable or expression, which fails to compile with the error "variable length
> arrays are not supported in HLSL". For a minimal example `int array[10]` works but
> `int array[(10).x]` doesn't. This makes it impossible to use components of constant
> vectors as array lengths.
>
> This works in FXC and is causing us issues when porting shaders to DXC.

Body links a shader-playground permalink (a third-party site; may or may not still resolve).

## Comments

1. **llvm-beanz, 2023-11-09** — posts a Compiler Explorer link. Its stored source (read back
   via `GET /api/shortlinkinfo/Mjh4e1G7b`, i.e. from the API and not from a compiler run) is a
   six-case matrix with the maintainer's own annotation *"Only array1 and array3 compile
   without errors"*:

   ```hlsl
   static const uint  scalarLength   = 10;
   static const uint2 vectorLengths  = uint2(20, 30);
   ...
   int array1[10];                  // annotated OK
   int array2[(10).x];              // annotated fails  <- the body's minimal case
   int array3[scalarLength];        // annotated OK
   int array4[scalarLength.x];      // annotated fails  <- swizzle of a SCALAR
   int array5[vectorLengths.x];     // annotated fails
   int array6[vectorLengths[1]];    // annotated fails  <- [] indexing, not swizzling
   ```

   Compiled at `-T ps_6_6`. This is a **wider** claim than the body: it says a `.x` on an
   already-scalar `static const` also fails, and that `[i]` indexing fails as well as `.xyzw`
   swizzling.
2. **devshgraphicsprogramming, 2024-05-16** — "Affects #6144 in a tangential way".
3. **s-perron, 2024-05-21** — "Are there any plans to fix this soon?"
4. **llvm-beanz, 2024-05-21** — "it isn't on our priority list."

No maintainer has said this is by design, and none has said it is a bug. Comment 4 is a
priority statement, not a design position.

## Repro quality

**complete.** The body supplies a one-line minimal case that runs as-is once wrapped in an
entry point, and comment 1 supplies a fuller matrix. Nothing had to be invented.

## The symptom, stated so it can be falsified

`repro.hlsl` is the body's minimal case:

```hlsl
float4 main() : SV_Target {
    int array[(10).x];
    ...
}
```

**Reproduces** iff dxc rejects it with `variable length arrays are not supported in HLSL`
(the exact diagnostic named in the body).

**Does not reproduce** iff dxc compiles it and emits DXIL.

Deliberately *not* the predicate: "the compile failed", or "exit code is nonzero". On Windows
dxc returns E_FAIL (0x80004005) for every ordinary diagnosed error, so "failed" cannot tell
this diagnostic apart from a syntax error, an unknown profile, or an unrelated rejection by an
old release. The predicate must name this diagnostic. Its control is `control-literal.hlsl`
(`int array[10]`, the body's own working case) run with `--expect no-match`.

## What else I intend to establish, before deciding what the defect actually is

The title says *component swizzling / vector indexing*. The body says *"a component of a
constant variable or expression"*. Comment 1 says a `.x` on a **scalar** fails too. Those are
three different rules, and at most one of them is what the compiler implements. So:

- literal vs `static const` operand;
- `.x` swizzle vs `[0]` subscript;
- scalar vs vector vs matrix operand;
- one component vs a multi-component swizzle (`.xy`) used where a scalar is wanted;
- and, critically, **array bound vs other constant-expression contexts** — a `case` label, a
  `vector<T,N>` / template argument, a global or `groupshared` array bound, `[numthreads(...)]`.
  If only the array bound rejects it, "not considered a constant expression" is the wrong
  description of the defect and the issue text is misleading even though the report is real.

Any of these turning out differently from the title/body is a **finding to flag**, not a
detail. Likewise: if the construct is rejected in Sema by deliberate code with a comment
saying so, then the correct verdict is a language-design question, not a bug, and this triage
must say which it is rather than assert one.

## History

Bisection floor is v1.4.1907. Nothing here needs a modern shader model, so the repro will
target the **oldest** profile that still shows the behaviour (`ps_6_0`) rather than the
`ps_6_6` of comment 1 — a release that predates the profile is an invalid probe, not evidence.

Expected shape: the report is from 2021 and the last maintainer comment (2024) does not claim
a fix, so `always-repro'd` is the likely history. That is a prediction, not a result.

## FXC

The body says FXC accepts this and the issue carries `fxc-disagrees`. That claim is
**untested** as of writing this file and must be measured, not repeated — an FXC pane beside
DXC on Compiler Explorer shows the disagreement instead of asserting it. FXC needs
`/T ps_5_0 /E main` style arguments, and needs its own control, exactly as a Clang pane does.

## Clang

HLSL is being rebuilt in clang, so "has the successor already answered this?" is the more
useful question for a language-semantics issue. A Clang pane is worth trying, with the caveats
that (a) a Clang error is not evidence until a trivial control with the same flags compiles
clean, and (b) clang's backend cannot lower a pixel shader writing `SV_Target`, so a compute
restatement is likely required.
