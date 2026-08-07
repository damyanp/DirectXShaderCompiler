# Method notes — #2918

Observations about the *procedure and tooling*, not the issue. Recorded, not fixed.

## 1. `cmd.txt` cannot express a two-stage repro, and this issue needs one

The harness contract is one `dxc` invocation per line, arguments only, executed as
`<compiler exe> <args>`. #2918's symptom lives in a **PIX DXIL pass**, which runs *after*
compilation through `IDxcOptimizer::RunOptimizer` — a different executable (`dxopt.exe`) over
the *output* of the dxc line. There is no way to say that in `cmd.txt`.

Consequences, all deliberate:

- **No `match.json` was written**, so every capture is `unscored`. Writing an
  `internal_failure` predicate would have scored the *stage-1 compile* — which succeeds on
  every release, including the one that reproduces — and produced a confident, wrong
  "fixed at v1.4.1907, no-repro everywhere" reading. `classify()` (`triage.py:752`) documents
  `unscored` as first-class; precedent in #3150 and #2427.
- **`bisect` is unusable** for the same reason. History was measured by hand
  (`run-pix-passes.py --history` → `manual-case-history.txt`), following #2128's
  `measure.py` + `manual-case-*.txt` pattern.
- `cmd.txt` still carries the stage-1 line, so `run --issue` produces a real `out-main-debug.txt`
  and `audit` sees `repro.hlsl` as covered. The file's comment block says what stage 2 is.

This is the third issue in this workspace to need a hand-rolled harness. The pattern
(`<harness>.py` + `manual-case-<topic>.txt` with a `# case:` / `# harness:` / `# why not
triage.py bisect:` / `# ran:` / `# verdict: unscored` header) is now well established and
worked cleanly; the gap is that nothing in `triage.py` knows those files exist, so `audit`
cannot tell a well-evidenced manual case from an issue where somebody simply never measured
anything.

## 2. Releases ship no `dxopt.exe`, so old builds need a mixed pairing

Release packages contain `dxc.exe`, `dxcompiler.dll`, `dxil.dll` and nothing else. To drive an
old `dxcompiler.dll`'s PIX passes you must put **this repo's** `dxopt.exe` next to it in a
scratch directory and let DLL search order do the rest. `dxopt` touches only
`DxcCreateInstance` and `IDxcOptimizer`, which are stable, so this works — but it is a
cross-version pairing, and "it should be fine" is not evidence.

The per-build **baseline + control** pair is what makes it falsifiable: baseline (same module,
no passes) must succeed, control (same module with a deliberately broken `!dbg`, no passes)
must fail. If the pairing were broken, or the old build simply didn't run the check, the
control would silently pass and the "no-repro" result would be worthless. Any future probe of
a release-only binary through a tool the release does not ship should carry the same pair.

`DXC_TRIAGE_CACHE` and the release layout (`<cache>/releases/<tag>/bin/x64`, but
`<cache>/releases/v1.4.1907` flat) are stable enough to script against; the layout difference
is worth knowing before writing a loop.

## 3. A verifier check that silently does not run — this cost a wrong control

The first control was written as "delete `inlinedAt:` from a `!DILocation`" and it **passed**,
which looked like the check no longer existed. It does. `Verifier::visitDISubprogram`
(`lib/IR/Verifier.cpp:975-1000`):

```cpp
DILocalScope *Scope = DL->getInlinedAtScope();
if (Scope && !Seen.insert(Scope).second) continue;
DISubprogram *SP = Scope ? Scope->getSubprogram() : nullptr;
if (SP && !Seen.insert(SP).second) continue;   // same node -> insert fails -> check SKIPPED
Assert(SP->describes(F), "!dbg attachment points at wrong subprogram for function", ...);
```

When the location's scope **is** a `DISubprogram`, `Scope` and `SP` are the same node, the
second `Seen.insert` fails, and `continue` skips the assert. A genuinely illegal `!dbg` is
accepted, by `opt -verify` and by `dxopt` alike. The check only fires when the scope is a
`DILexicalBlock` — which is exactly the shape in the reporter's dump (`!965`).

Generalisation worth carrying: **a control that passes is not evidence that the checked
behaviour is absent** until you have shown the check can fire at all. Pick the control's shape
from the reported artefact, not from what is convenient to edit.

## 4. `dxopt` throws away the failure text

On a failing `RunOptimizer`, `dxopt` prints `Operation failed - error code 0x80004005.`, exits
1, writes nothing to stderr, and **discards the text blob `RunOptimizer` returned** — which is
where the verifier's message lives. True of the Debug build too. Anyone triaging a PIX pass
failure through `dxopt` will see an HRESULT and no diagnosis, and will need this repo's
`opt.exe -verify -S` to recover the message. Worth knowing before concluding "it fails but
says nothing, so we cannot tell what went wrong".

Related: `report_fatal_error` becomes `hlsl::Exception(DXC_E_LLVM_FATAL_ERROR = 0x80AA001B)`
(`lib/Support/ErrorHandling.cpp:117`), but the HRESULT that reaches `dxopt` is plain `E_FAIL`
`0x80004005`. Do not key anything on the specific code.

## 5. One release crashes on the deliberately-broken control

v1.6.2106's `dxcompiler.dll` exits `3221226505` (`0xC0000409`, STATUS_STACK_BUFFER_OVERRUN) on
the broken-metadata control, where every other release returns `E_FAIL`. It handles the real
inputs fine. Harmless here — the control's requirement is "must fail" and a crash is a failure
— but a control that asserts a *specific* exit code would have flagged v1.6.2106 as a broken
probe. `internal_failure`-shaped requirements should stay shape-based, which is the same point
`SKILL.md` makes about crash predicates.

## 6. Compiler Explorer cannot show this class of defect at all

Two independent walls, both worth recording because neither is about this issue:

- CE runs `dxc` only. Any defect in a **post-compile pass driven through `IDxcOptimizer`**
  (all of `lib/DxilPIXPasses/`, and anything else reached via `RunOptimizer`) is out of reach
  there, no matter how good the repro is.
- CE's oldest DXC is `dxc_1_6_2112`. For anything fixed before 2021-12 the broken side simply
  cannot be shown, so a CE link can only ever demonstrate the *current* behaviour.

A link was still published, because the shader is agent-written and public and the metadata it
prints (`inlinedAt:` on the `!DILocation`s scoped to the callee's `DISubprogram`) is exactly
the thing whose absence was the bug. `godbolt-note.txt` opens by saying both walls out loud so
a reader does not go looking for a failure that cannot appear there. `--skip` would also have
been defensible; the note seemed more useful than a blank.

## 7. Working with a repro that must never be obtained

The issue names an internal bug number and a private shader. That was treated as a hard stop:
not searched for, not asked after, nothing derived from it written down beyond the public
dump already in the issue text. The workable substitute was to read the *dump* as a
specification — `column: 1`, no `inlinedAt:`, lexical-block scope — and reconstruct an input
with those properties. Two things made that honest rather than decorative:

- the reconstruction is named as one in `repro.hlsl`'s header, in `godbolt-note.txt`, in
  `notes.md` and in `comment.md`, every time it is mentioned;
- it is only load-bearing because it **positively reproduces** on v1.5.2010. A reconstruction
  that merely fails to reproduce everywhere would have been worth very little, and the honest
  verdict then would have been `needs-repro-from-reporter`.

Note for whoever writes the "unavailable repro" guidance: the deciding factor was not
cleverness in building the shader, it was that the public dump contained enough *structural*
detail (a hard-coded column, a missing field) to identify the code that produced it. When a
dump has that, a reconstruction is checkable; when it has only a message, it is not.

## 8. Small things

- `repro.hlsl`'s comment header is load-bearing: with `-Zi` the whole source text is embedded
  in `!DIFile`/module metadata and every `line:` in the captured output refers to it. Editing
  the comments silently desynchronises every line number in `out-main-debug.txt`,
  `manual-case-history.txt` and `godbolt-note.txt`. `SKILL.md` warns about this; it is even
  sharper when the evidence *is* metadata.
- `audit --issue` reported "no missing evidence" while `notes.md`, `comment.md` and the verdict
  were all still absent — `audit_issue` returns early when `verdict.json` does not exist, so
  those four checks never ran. A clean audit before the verdict is recorded means nothing;
  it is only meaningful afterwards. Worth an explicit line in the skill, since the natural
  worker instinct is to run `audit` as a "am I done yet?" check.
- The label taxonomy has `PIX` ("Issues related to PIX passes") and `debug info`, both apt and
  neither applied here — this issue carries no labels at all.
