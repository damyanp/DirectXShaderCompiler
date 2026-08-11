# #4710 — what "this reproduces" means

Written **before** running any compiler, from the issue text alone
(<https://github.com/microsoft/DirectXShaderCompiler/issues/4710>, filed 2022-10-06 by
`kylawl`).

## Reported symptom

DXC emits a diagnostic **it should not emit**:

```
error: Index for resource array inside cbuffer must be a literal expression
```

for a shader that indexes a resource array declared **inside a `cbuffer`** with a loop
induction variable, where the loop is marked `[unroll]`.

The polarity is inverted relative to a normal repro: the reporter's claim is that a shader
which *ought to compile* is **rejected**. So:

* **`repros`** = that exact diagnostic string appears on the reporter's input.
* **`does-not-repro`** = the shader compiles (no such diagnostic).

## What the reporter says, and what is therefore in scope

The issue body distinguishes three indexing forms and states three different results:

| # | construct | reporter's claim |
| --- | --- | --- |
| A | `foo_bar.Texture[i]` — array member of a struct that is an element of an array **inside** `cbuffer` | DXC errors; FXC (`ps_5_0`) compiles |
| B | `FooBarTextures[i]` — resource array declared directly **inside** `cbuffer` | DXC errors; FXC (`ps_5_0`) compiles |
| C | `NotFooBarTextures[i]` — resource array at **global** scope (outside `cbuffer`) | DXC **and** FXC compile; but it does not fit the reporter's binding system |

So the repro must exercise A and B, and C is the reporter's own stated **negative control**:
if C also errors, my instrument is wrong, not DXC.

The reporter also states:
* occurs on `main` and in the July 2022 official release (v1.7.2207);
* `/HV 2016` makes no difference;
* command line `dxc.exe /E psMain /T ps_6_6`.

The reporter's own follow-up comment (2022-10-06) narrows the FXC claim: **none** of the
three forms work under FXC `ps_5_1` (FXC returns without an error but emits no file); they
work under FXC `ps_5_0`. That is important — the FXC comparison the title rests on is a
`ps_5_0` comparison, i.e. against the pre-`ps_5_1` binding model that has no descriptor
ranges. I will note but not adopt that claim as measured, since I have no FXC here.

## The hazard I must not fall into

The symptom **is a diagnostic**. Therefore:

* "nonzero exit" is worthless as a predicate — dxc returns `E_FAIL` (0x80004005) for every
  ordinary diagnosed error, including a plain syntax error.
* "an `error:` line appeared" is worthless for the same reason, and much worse across
  releases: any release predating some construct in the repro will emit *some* error, and a
  loose predicate scores that as a textbook reproduction, manufacturing an
  "always reproduced" history for a feature that did not exist.
* The `invalid-probe` safety net **cannot** help here, because for a diagnostic issue the
  demotion signal and the symptom are the same class of observation.

So the predicate must match the **exact** diagnostic text, and every release must be
accompanied by a **positive control** — a construct I have established should compile — run
on the *same* binary. A release that fails the control did not measure this issue and is
disqualified rather than counted.

## Predicate I intend to write (before measuring)

`contains` on the literal string:

```
Index for resource array inside cbuffer must be a literal expression
```

anchored so it cannot be satisfied by an unrelated failure. No `nonzero_exit`, no
`internal_failure` (nothing here is crash-shaped), no bare `error:`.

## Controls I intend to run

| label | shader | expectation |
| --- | --- | --- |
| `global-array` | form C: dynamic index into a **global** resource array | `no-match` — reporter says this works |
| `literal-index` | form B with a literal index instead of `i` | `no-match` — the diagnostic explicitly asks for a literal |
| `hello` | trivial `ps_6_6` shader, no resources | `no-match` — proves the profile/toolchain runs at all (per-release feature-presence control) |

`literal-index` is the strongest of the three: it differs from the failing case in exactly
the property the diagnostic names.

## Repro quality

`complete` — the issue body carries a self-contained shader and the exact command line. I
will use the reporter's `-T ps_6_6 -E psMain` for the primary capture, and separately measure
whether an older profile also shows it (for history reach), recording any deviation.

## The second question, which is not a measurement

Whether the diagnostic is **wrong** is a language-semantics question, not something the
compiler's output can settle: resource arrays inside constant buffers have real restrictions
(a `cbuffer` is a single binding; a resource inside one has no descriptor range of its own to
index). The reporter themself links to the emitting source line. So the deliverable is:

1. the measurement (does the exact diagnostic still fire, and since when);
2. the **source-level guard** that emits it — file, function, condition — so a maintainer can
   judge whether the restriction is intended;
3. an honest statement if (2) does not settle whether the error is correct. In that case
   `needs-human-judgement` is the right suggested action and I will not manufacture certainty.

I am explicitly *not* going to conclude "the compiler is wrong" merely because FXC `ps_5_0`
accepted it, nor "the compiler is right" merely because a guard exists.
