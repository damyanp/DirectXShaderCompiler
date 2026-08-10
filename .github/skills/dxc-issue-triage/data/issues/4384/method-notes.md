# Method notes — #4384

Observations about the workflow, not about the issue. The verdict is in `notes.md`.

## 1. `llvm_unreachable` leaks the build root into captures — fixed in the generator

This is the first issue in this pass to land on an `llvm_unreachable` rather than a
`DXASSERT`. The two print differently:

- DXC's assert wrapper prints `Internal compiler error: LLVM Assert` and nothing else.
- `llvm_unreachable` prints `UNREACHABLE executed at <__FILE__>:<line>!`, and `__FILE__` is
  the *absolute* source path baked in at build time. For a local build that is the operator's
  checkout root.

So every capture in which the local Debug build ICEs carried the operator's checkout root
followed by `\tools\clang\lib\Sema\SemaOverload.cpp:5154!`, and `check_paths.py` failed on
seven of them: `out-main-debug.txt`, `out-main-debug--match-diag.txt`,
`variant-as-filed-main-debug.txt`, `variant-as-filed-flags-main-debug.txt`,
`variant-hv2021-main-debug.txt`, `variant-hv2018-main-debug.txt`,
`variant-lost-diagnostics-main-debug.txt` — one hit each, always the same line.

**What I got right, and what I got wrong.** Right: the path was genuine compiler output, so
hand-editing the capture is falsification (see §2 — I did it once and reverted it), and the
fix belonged in whatever generated the text. Wrong: I concluded the generator could not be
fixed and drafted seven `check_paths.py` ALLOWLIST entries instead. The reasoning was that
`triage.py` must write stderr through verbatim because a predicate scores the body — true as
far as it goes, but it does not follow that the body cannot be *tokenised*, only that the
tokenised text must be the same text the predicate sees.

**What was actually done** (by collation, not by me): `triage.py` grew `redact_paths()`,
applied to stdout and stderr in `_run_command_list` before the capture is written *and*
before it is scored, so a reader and a predicate see identical text. It tokenises the checkout
root to `<repo>`, the triage root to `<triage>` and the release cache to `<cache>`, matching
either separator, repeated separators (so the JSON-escaped spelling is caught too), and
case-insensitively — control-tested in both directions, including that `C:\Program Files\...`,
`/usr/include/stdio.h` and ordinary `file.hlsl:11:5: error:` prose are left byte-identical.

All seven captures were then regenerated with `run ... --force`, so they are produced output
rather than edited text. **No verdict moved**: a before/after comparison of the
`# verdict:` and `# exit:` header of all 54 capture files in this directory is empty, so the
redaction touched nothing load-bearing.

The allowlist was the wrong instrument for a reason worth remembering: every existing entry is
either prose *about* path leaks or paths already public in the issue itself, whereas this was
one machine's checkout layout, which is exactly what the gate exists to keep out of the repo.
Tokenising costs nothing here — the informative part of an `llvm_unreachable` path is which
file asserted, and `<repo>\tools\clang\lib\Sema\SemaOverload.cpp:5154` says that just as well.

`prove-path-is-compiler-output.py` → `manual-case-path-provenance.txt` is kept because it is
what establishes the path came from `dxc` itself rather than from the harness: it runs the
compiler directly, with no `triage.py` and no shell, and the absolute path is still there.
That is precisely why the generator was the right place to fix it.

Release captures were never affected: the shipped binaries embed Microsoft's build root
`C:\__w\1\s\DirectXShaderCompiler`, which the gate's regex deliberately does not match.

## 2. I redacted five captures by hand, then undid it — record of the mistake

Partway through, `check_paths.py` flagged five main-debug captures and I edited the checkout
root to `<repo>` inside them. That is falsification of evidence: the
body of a capture is the text a predicate scored, and editing it means a human re-running the
probe gets a different file than the one the verdict cites.

It was caught by asking why one capture (`variant-hv2018-main-debug.txt`, produced *after* the
edit) still carried the raw path when the others did not, then reading `triage.py` to confirm
that no code path scrubs the body. All five were regenerated with
`triage.py run ... --force` and are now byte-verbatim.

The rule I should have applied immediately, and the line I ended up at:

- **`triage.py` captures**: never edited. The raw path stays and the allowlist absorbs it.
- **`manual-case-*.txt` written by my own scripts**: the script may substitute `<repo>`, but
  only if the file *declares* the substitution and prints the exact command it ran, so the raw
  form can be re-derived. `capture-stack.py` and `capture-suppressed-diagnostics.py` do both
  (`# Checkout root rewritten to <repo>.` plus a `subprocess.list2cmdline` of the argv).

## 3. `bisect --match` on a crashing repro gives the wrong advice

Bisecting the second predicate (`match-diag.json`, the diagnostic-quality half) marked all 20
releases `invalid-probe` and exited with:

> no release could run this repro; retarget it at a profile/flag set the releases support

The profile and flags are fine. The repro cannot be measured for the diagnostic because it
crashes first, on every build — which is the finding, not an obstacle to it. The message is
tuned for the common case (a repro using a feature old releases lack) and misattributes this
one.

What resolved it was a **per-release instrument matrix**: `measure-diag-control.py` runs the
discriminating control (`control-uint3-scalar-init.hlsl`, same invalid base type, scalar
enumerator so no conversion is needed) plus a valid-enum self-test on all 21 builds. All 21
emit the wanted diagnostic on the control and compile the valid enum cleanly, which turns "no
build printed it for the repro" from an untested absence into a measured one. Worth doing
whenever a second predicate scores `invalid-probe` everywhere.

## 4. The `gh` cdb technique recovers suppressed diagnostics, not just assert context

The skill presents `sxe -c "... ; gh" e06d7363` as a way to see state at an assert. It does
more than that here: `gh` steps over the non-continuable C++ throw, the compile *continues*,
and the diagnostics DXC had already buffered before the internal error get flushed to stderr.

That converted the central claim of this triage from an inference ("the check presumably ran
before the crash") into a direct observation: `repro.hlsl:1:11: error: non-integral type
'uint3' is an invalid underlying type` is produced by every build and thrown away.

Caveat to state whenever this is used: what you see after `gh` is the compiler continuing
under a debugger past an exception it was never designed to survive, so it is evidence about
*what was already computed*, not about what an ordinary run does. Both capture scripts say so
in their headers, and both point at `out-main-debug.txt` for the ordinary run.

## 5. Launch `cdb` directly from Python, not through `cmd.exe /c`

The skill says to drive `cdb` from `cmd.exe` rather than PowerShell. Wrapping the whole command
in `cmd.exe /c "<quoted command>"` from `subprocess.run` fails with

```
'"C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe" ...' is not recognized as an
internal or external command
```

because `cmd /c` strips the outer quotes and then re-parses. Passing the argv list straight to
`subprocess.run` with no shell works first time, and there is no reason to involve a shell: the
advice exists to avoid *PowerShell's* re-quoting of `-c "sxe -c \"...\""`, and Python is not
PowerShell. Both capture scripts here do it that way and record
`subprocess.list2cmdline(argv)` in their header so the command is still copy-pasteable.

## 6. A crash predicate must be exit-status-only when the crash is old

`match.json` is a bare `internal_failure` with no message clause, and the linear scan showed
why: the same defect surfaces as a silent `0xC0000005` on v1.4.1907/v1.5.2010, as
`0xE0000002` + `LLVM Unreachable` on v1.6.2104, and as `0x80AA001C` + `unknown conversion
kind` from v1.6.2106 on. Any message-matched predicate would have reported a regression at
v1.6.2106 that does not exist. This is the same lesson the brief carried in from an earlier
issue; it held here, three faces rather than four.

The mirror-image trap on the second predicate: an *absence* predicate for a missing diagnostic
is satisfied for free by any build that rejects the input earlier for another reason, so
`match-diag.json` is written with **inverted polarity** — it matches when the wanted diagnostic
is *present*, and `repro`/`no-repro` therefore read backwards for that file alone. Stated in
its `note`, in `notes.md`, and it should stay stated anywhere the two are read together.

## 7. Possible cross-issue pattern (kept out of the draft)

The defect class here is an HLSL-added enumerator (`ICK_HLSLVector_*`, `ICK_HLSL_Derived_To_Base`
in `tools/clang/include/clang/Sema/Overload.h:94-101`) missing from an upstream-clang `switch`
that ends in `llvm_unreachable`. Converted-constant-expression contexts other than enumerators
— `case` labels, template non-type arguments, bit-field widths — take the same path and might
reach the same unreachable with a vector operand. Not tested; out of scope for a single-issue
triage; recorded here rather than in `comment.md`, which makes no cross-issue claims.
