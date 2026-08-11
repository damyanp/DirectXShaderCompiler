# Issue 4514 — "Variable inside a namespace not found"

Written **before** running any compiler, from the issue text alone.

## What the reporter says

Filed 2022-06-16 by `bioglaze` against "DXC version December 2021" (i.e. the
v1.6.2112 release). The shader is complete and self-contained:

```hlsl
namespace testNamespace
{
    cbuffer testBuffer
    {
        uint testVariable;
    }

    // Uncommenting the following line somehow fixes the issue
    //Texture2D testTexture;
}

[numthreads(1, 1, 1)]
void main( in uint3 tid : SV_DispatchThreadID )
{
    if( testNamespace::testVariable * tid.x > 0 )
        return;
}
```

Reported failure:

```
Error : no member named 'testVariable' in namespace 'testNamespace'; did you mean simply 'testVariable'?
```

No target profile, entry point or language-version flag is given, but
`[numthreads(1,1,1)]` + `void main(...)` fixes the stage as a compute shader
with entry point `main`. The reporter's build (Dec 2021) defaulted to
`-HV 2018`; **no `-HV` is stated anywhere in the report**, so the repro should
carry none unless measurement shows one is needed.

## Thread

- 2023-07-14 `llvm-beanz` (COLLABORATOR): "Reproduced on trunk with godbolt".
- 2024-08-29 `bioglaze`: "still active with the July 2024 version".
- 2025-04-22 `hekota` (MEMBER): names #7322 as related/duplicate, and adds the
  sharper statement of the bug: with the texture commented out `testVariable`
  is found **only by its unqualified name**; uncommenting the texture makes the
  **qualified** name work too. "Definitely a bug."

So the thread asserts the bug is live as of at least mid-2024, and a maintainer
restated (not retracted) it in 2025.

## What "this reproduces" means

**Primary symptom (`match.json`).** Compiling the shader exactly as filed, as
`-T cs_6_0 -E main`, produces a `no member named 'testVariable' in namespace
'testNamespace'` error. The compile fails; no DXIL is produced.

This is a *diagnostic-quality* issue: the reported symptom **is** an error
message. Two consequences I must respect:

1. The `invalid-probe` classifier keys on feature-absence markers such as
   `no member named` — which is literally this issue's symptom. `classify`
   suppresses the demotion when a positive clause of `match.json` quotes the
   marker verbatim, so `match.json` must contain the **exact** diagnostic text
   rather than an approximation. I must read the capture headers for
   `# invalid-probe-reason:` and check the demotion did not fire.
2. Conversely a release that *fixes* this emits no diagnostic and scores
   `no-repro` — which is the correct reading here, not an instrument failure.

## Decomposition and the controls the report itself supplies

The report contains its own A/B, which makes unusually good controls:

| case | expectation from the issue text |
| --- | --- |
| `repro.hlsl` — texture commented out, qualified reference | **fails** with the quoted diagnostic |
| texture declaration **uncommented**, qualified reference | **compiles clean** ("somehow fixes the issue") |
| texture commented out, **unqualified** `testVariable` | **compiles clean** (hekota, 2025-04-22) |

The second and third are `--expect no-match` controls. If either of them also
fails, my reconstruction is wrong and nothing else I measure means anything.

A fourth control is worth running for the opposite reason: a cbuffer at
**global** scope referenced by its member name, to show the predicate is not
firing on everything.

## Predicate hazards I expect to have to handle

- **Absence-clause trap does not apply**: the symptom is a *presence* (an error
  string), so a failed compile cannot satisfy it for free. But the mirror is
  live — the predicate must not be satisfiable by *any* error, so it must quote
  the namespace-lookup diagnostic and not merely `error:`.
- **A language-version flag would be a hazard, not a help.** The issue names
  none. If I add one, an old release that does not know the flag or the version
  is demoted to `invalid-probe` and every release before it silently looks
  "fixed" — a fake version floor. If a flag turns out to be needed, I must show
  it is load-bearing for the symptom, and if it is not, drop it and re-measure.
  The forward-in-time mirror also has to be checked: today's default is
  `-HV 2021` where the reporter's Dec-2021 build defaulted to `-HV 2018`, so I
  must confirm the current default does not reject the shader for an unrelated
  reason before reading anything into a `main` result.
- The bisection floor is v1.4.1907 (2019-07), which predates the report by
  three years, so a full history should be reachable if `cs_6_0` and namespaces
  both exist that far back. `namespace` is not new syntax, so I expect no
  profile/feature demotions — but that is a prediction to test, not an
  assumption.

## Repro quality

`complete` — the issue body carries a whole compilable shader plus the exact
diagnostic; only the (unambiguous) profile and entry point have to be supplied.

## What each outcome would mean

- **repros on main** — expected from the thread; then the question is the
  history, and specifically whether it has *always* been broken (likely, since
  no comment ever reports it working) or regressed at some point.
- **does-not-repro on main** — would contradict a 2025-04 maintainer comment,
  so before believing it I would have to rule out that today's `-HV 2021`
  default changed the parse, and check whether the diagnostic merely moved
  (`changed-behavior`) rather than the lookup being fixed.
- **changed-behavior** — e.g. the qualified reference now compiles but produces
  the wrong constant-buffer load, or a different diagnostic appears.
