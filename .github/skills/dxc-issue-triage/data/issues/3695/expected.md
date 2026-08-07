# #3695 — DXC Crash on Bad Shader

Written **before** anything was run, from the issue text alone.

## Source

- Body (2021-04-19, pow2clk), from a forums question:
  <https://forums.xboxlive.com/questions/121031/dxc-compiler-crash-on-invalid-compute-shader.html>
- Attachment `shader.txt`
  (<https://github.com/microsoft/DirectXShaderCompiler/files/6338441/shader.txt>), saved here
  as `attachment-shader.txt`.
- Comment 1 (2021-11-18, pow2clk) pastes the same shader inline "for convenience".
  Byte-comparable to the attachment.
- Comment 2 (2024-07-16, damyanp): *"Repros on latest: <https://godbolt.org/z/jehx1f56z>"*.
  That saved CE session is `dxc_trunk` with `-T cs_6_6` (no `-E`), i.e. a different profile
  from the one in the body. Fetched from `/api/shortlinkinfo/jehx1f56z`; its source is the
  same shader.

## What the issue claims

> Shader code is invalid - shouldn't compile successfully, but crashes DXC without providing
> an error message. Seems to be related to assigning one `RWTexture2D<float4>` global
> variable to another.

Command line as filed:

```
dxc /Tcs_6_0 /Emain shader.txt
```

The invalid constructs in the shader are, at minimum:

- `blur()` is declared to return `RWTexture2D<float4>` and does `return tex;` — returning a
  resource object by value from a user function;
- `RWTexture2D<float4> filterFog = blur(...)` — a local resource variable initialised from
  that call;
- `_blurResult = filterFog;` — assignment to a global resource object, which is what the
  reporter fingers as the trigger.

## What "this reproduces" means

**The compile ends in an internal compiler failure** — DXC crashing or asserting rather than
emitting a diagnostic. Concretely, any of:

- an assert firing in the Debug ground-truth build (exit `0x80000003` trap or `0xE0000001`
  C++-exception form);
- an access violation (`0xC0000005`) or other structured exception;
- `llvm_unreachable` / `report_fatal_error` (`0xE0000002` / `0xE0000003`);
- an `llvm::cast<X>() argument of incompatible type!` failure, which arrives as **E_FAIL
  (0x80004005)** and is therefore only distinguishable by its text;
- on Linux/Compiler Explorer, death by signal (139 / 134).

## What does **not** count as reproducing

- **A plain diagnosed error.** dxc exits `0x80004005` (E_FAIL) for ordinary `error:`
  diagnostics. Since the shader *is* invalid, the correct behaviour is a diagnostic and a
  nonzero exit — so a nonzero exit on its own is not the symptom, and must not be treated as
  one. The issue's own words are that it "crashes DXC **without providing an error
  message**".
- A successful compile is likewise not the symptom, but *would* be its own defect (invalid
  code accepted). If that is what happens now, the verdict is `changed-behavior`, not
  `does-not-repro`.

So the predicate must be `internal_failure` (exit status first, text markers only as a
backstop), never "nonzero exit" and never a match on any particular assert message: the same
defect shows as a trapped assert in Debug and as an access violation or a bare E_FAIL cast
error in the Release binaries this history is bisected over.

## Second predicate, if needed

If the current build emits a clean diagnostic instead of crashing, that is
`does-not-repro` for the crash. If it emits *neither* a crash nor a diagnostic (compiles
successfully), the issue's other half — "shouldn't compile successfully" — is still live and
needs its own predicate and its own bisection.

## Repro quality

**`complete`** — the reporter supplied a self-contained shader plus the exact command line,
and a collaborator re-pasted it inline. Nothing had to be constructed.

## Configuration questions to settle while building the repro

- The body says `cs_6_0`; damyanp's 2024 CE link says `cs_6_6`. Use the reporter's `cs_6_0`
  for `cmd.txt`; check `cs_6_6` separately rather than silently substituting it.
- The filed command uses `/`-style flags and a `.txt` input. `/T` and `/E` are the same
  options as `-T`/`-E`; the extension should be irrelevant, but that is an assumption to
  test rather than assert, so capture a control on the original `.txt` file.
- No workaround flags were used by the reporter, so there is none to question.

## History expectations (to be tested, not assumed)

`cs_6_0` exists in every release back to the v1.4.1907 floor, so no profile-driven
`invalid-probe` is anticipated — but that must be read out of the captures, not assumed.
