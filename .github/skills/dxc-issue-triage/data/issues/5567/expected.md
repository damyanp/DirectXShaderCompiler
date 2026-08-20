# Expected symptom (#5567)

**Repro quality: complete.** The issue gives the exact repro shader and command line.

## What the issue asks

`-Wcomma-in-init` (`warn_hlsl_comma_in_init`, "comma expression used where a
constructor list may have been intended") fires for

```hlsl
[numthreads(1, 1, 1)]
void main()
{
  uint2 a = (1, 2);
}
```

but does **not** fire for

```hlsl
[numthreads(1, 1, 1)]
void main()
{
  uint2 a = (1, 2) / 2;
}
```

compiled with `dxc -T cs_6_6 repro.hlsl -Od`, even though `(1, 2)` is almost certainly
the same forgotten-`uint2(...)` typo, just wrapped in a division. The reporter is not
claiming a crash or wrong codegen — the shader compiles and generates code either way —
only that the diagnostic is too narrow: it only looks at the initializer expression
itself, not at a comma expression nested inside a larger expression that is the
initializer.

## What "this reproduces" means here

`this reproduces` = compiling the **Steps to Reproduce** shader
(`uint2 a = (1, 2) / 2;`) with `main-debug` produces **no** `-Wcomma-in-init`
diagnostic (no `comma expression used where a constructor list may have been
intended` in the output), while the **direct** case `uint2 a = (1, 2);` (no
division) still **does** produce that diagnostic on the same compiler. The second
half is a same-subject positive control: without it, "no warning" on the reporter's
shader could just as easily mean the whole diagnostic was removed, which would be a
regression, not confirmation of the reported gap.

`does-not-repro` would mean the division-wrapped case now also emits
`-Wcomma-in-init` (i.e. DXC's Sema was made more aggressive, per the issue title).

This is a diagnostic-quality enhancement request, not a crash/miscompile issue, so
`internal_failure` does not apply; `match.json` is a `not_contains` predicate anchored
on the exact diagnostic group text, with the direct-comma shader as the required
positive control proving the pipeline (and the diagnostic itself) still exists.

Maintainer comment (damyanp, 2024-10-09) says "clang current does emit a warning in
these cases" — referring to the from-scratch HLSL front end being built in the
upstream `llvm-project` Clang, a different codebase from this repository. That is
checked via a Compiler Explorer `hlsl_clang_trunk` pane in step 7, not via `bisect`
(this repo's `main` and Clang's HLSL front end are unrelated source trees).
