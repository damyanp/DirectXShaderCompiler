# #3439 — Better demangling for improved error messages

Written **before** running any compiler, from the issue text alone.

## What the issue claims

pow2clk (2021-02-09): *"Certain error messages have less helpful mangled function names in
their output."*

The body gives a complete repro:

```hlsl
int CallMeMaybe(float, bool);

float4 main(float f : A) : SV_Target {
   return CallMeMaybe(f, false);
}

int CallMeMaybe(float f) {
    return 3;
}
```

and the reported output:

```
error: External function used in non-library profile:  \01?CallMeMaybe@@YAHM_N@Z
```

The ask: *"Either demangling this and other errors better than is currently available or
getting the information from eslewhere would make them more useful."*

Sole comment, llvm-beanz (2023-07-25, COLLABORATOR): *"We should probably just move this
diagnostic out of CodeGen and emit it in Sema where we have the AST name."* — i.e. the
maintainer's own reading is that this diagnostic is emitted **late**, from CodeGen, after the
AST-level name is gone.

No profile is stated in the issue. The shader has `SV_Target` and an `main(float f : A)`
signature, so a pixel profile is implied; the diagnostic text ("non-library profile") only
makes sense for a non-`lib_*` target.

## Repro quality

`complete` — the issue body carries a self-contained shader and the verbatim expected
diagnostic. Only the target profile has to be inferred, and the diagnostic text constrains it
to a non-library profile.

## "This reproduces" means

The compiler emits a diagnostic that contains a **mangled** function name rather than the
source-level HLSL name. Concretely, for the repro above:

1. the diagnostic `External function used in non-library profile:` is emitted (this anchors
   that we reached the specific message the issue is about — a failed parse cannot produce
   it), **and**
2. the function is named in Microsoft C++ mangled form — an identifier introduced by `?` and
   followed by `@@` and a type-encoding letter (`?CallMeMaybe@@YAHM_N@Z`), optionally with
   LLVM's `\01` no-further-mangling prefix — rather than as `CallMeMaybe` or a readable
   HLSL signature.

## "This does not reproduce" means

The same repro produces a diagnostic naming the function readably — `'CallMeMaybe'`, or
`int CallMeMaybe(float, bool)` — with no `?…@@…` token anywhere in the output. That is what
a fix for this issue looks like, and it is *also* what a wrong-configuration probe looks like,
so the diagnostic-text anchor above is mandatory.

## Deliberate hazards to avoid

- **A naive repro will look good.** Front-end Sema diagnostics (`no matching function for
  call to 'X'`, redefinition errors) print source-level names correctly. If I aim at those I
  will measure the wrong thing and wrongly conclude `does-not-repro`. The symptom lives in
  diagnostics emitted *after* mangling — CodeGen, the linker, the validator — which is
  exactly what llvm-beanz's comment says.
- **A bare "output contains `?`" predicate matches almost anything**, including
  `error: ... 'foo'?`. The predicate must be anchored on the `@@` mangling marker and must be
  given a negative control: a diagnostic I know is well-formed must *not* match.
- This is filed `enhancement` + `tech-debt`, so `repros` + `enhancement-not-bug` is the
  likely honest verdict — **unless** the message was improved since 2021, which a release
  bisect would date. A partial improvement (some messages demangled, others not) is a real
  and more useful outcome than a blanket verdict, so check more than one diagnostic path.

## Predicted answer (recorded so it can be wrong)

I expect the diagnostic still to carry the mangled name on `main`, because nothing in the
thread records a fix and the issue is still open with a 2024-07 milestone event. I have not
run anything yet.
