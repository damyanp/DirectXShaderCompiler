# Method notes from #4549

Findings about the *method*, not the issue. #4549 is a "the error message is misleading"
issue, which is a shape the method handles less well than a miscompile.

## 1. `error:` is not a portable anchor across release ages

The obvious predicate for "DXC blames the wrong resource" is "a line containing `error` also
contains the innocent resource's name". That clause **false-negatives v1.4.1907**: its DXIL
validator prints

```
error: validation errors
Resource depth_buffer with base 0 size 1 overlap with other resource with base 0 size 1 in space 0
```

— the substantive line has no `error:` prefix at all, because the prefix is on the summary
line above it. v1.5.2010 and later print `error: Resource depth_buffer …` on one line. So the
clause scored the oldest release `other-error`, which reads as "clean" when you skim a matrix,
on precisely the release that decides how far back the history goes.

Generalisation worth carrying: **the diagnostic *envelope* is as unportable as the diagnostic
*text*.** `error:`/`warning:` prefixes, whether a location is attached, and whether the
message is one line or two all move between releases and between the allocator and the
validator. Anchor on the nouns the message must contain, never on its framing.

The replacement clause is `\bdepth_buffer\b[^\n]*\b(?:register|space)\s+\d`. The **digit**
requirement is load-bearing for a second reason: HLSL source spells a binding `register(t0)`,
never `register 0`, so a clang caret line echoing the declaration cannot satisfy it. That
turned out to matter — under `-Zi` (and on Compiler Explorer, which appends it) the caret line
*is* an echo of `Texture2D<float> depth_buffer : register(t0);`.

## 2. For a diagnostic-quality issue, build a *non-diagnostic* predicate

The brief's hazard — "don't score a rewording as a fix" — has a stronger answer than
carefully-worded regexes: **find a measurement that contains no diagnostic text at all.**

Here that was the DXIL binding table. Declared `register(u0)`, printed `t0`. Zero words of
prose, immune to every rewording, and it happens to test the *cause* rather than the symptom.
`match-ignored-register.json` is a better predicate than `match.json` in every respect except
that it does not correspond to the sentence in the issue title.

The move that made it possible was **constructing a shader in which the reported symptom
cannot occur** — the acceleration structure at `u0` with nothing at `t0`, so there is no
collision and hence no message to read. The reporter's repro couples two things (the wrong
register class, and a collision); decoupling them showed the wrong register class is silently
accepted on its own, which is the finding that moved the verdict off `enhancement-not-bug`.

Worth generalising: when the complaint is about *how* the compiler talks, spend a control on
*what* it does. If the two disagree, the write-up is much stronger and the verdict is no
longer a matter of taste.

## 3. Anti-vacuity for a binding-table predicate is free

A `not_regex` for `u0` is trivially satisfied by a compile that failed for an unrelated
reason. Pairing it with the *positive* clause (a row for `opaque_as` showing `t0`) fixes that
without a separate control: the row only exists if the shader compiled *and* the resource
survived dead-code elimination to reach DXIL. The positive clause is the anti-vacuity anchor.

## 4. A "reworded, still broken" residual, and which direction to leave it in

No text predicate is airtight. The residual here is that a hypothetical fix which emits a new
*warning* about the register class but still lets codegen proceed to the collision would score
"still repros". That is the **safe** direction — it leaves an issue open that maybe deserved
closing, rather than erasing a live defect. Choosing which way a predicate fails is part of
writing it, and worth stating explicitly in `match.json`'s `note` fields.

## 5. `invalid-probe` can be two very different things

`bisect --linear` reported two unprobeable releases, and they needed opposite treatments:

- **v1.4.1907** — `use of undeclared identifier 'RayQuery'`. Genuine feature absence; the
  feature-presence control fails identically. Correctly excluded.
- **v1.5.2010** — exit `0xC0000005`, **empty output**. This is a *crash*, and its controls
  compile fine, so it is a second, unrelated defect masquerading as an unprobeable release.

Both print as one line in the bisect summary. The distinction only appeared because the
per-release matrix ran controls next to the repro on every build. A run that only probed the
repro would have shown two identical-looking gaps and no way to tell that one of them is a
finding in its own right.

The escape hatch for the first case was a **translation** of the repro into an older feature
set (`lib_6_3` + DXR 1.0 `TraceRay` instead of `ps_6_5` + `RayQuery`). That pushed the history
from 2021-04 back to 2019-07 and, incidentally, uncovered that the library-target message is
worse than the one reported. Translating a repro to dodge a feature floor is worth doing more
often than it is; the cost is one extra control per arm to prove the translation compiles at
all on the old release.

## 6. Small tooling frictions

- `triage.py compiler` has no `--list`; `--exe` is required, so it cannot be used to *inspect*
  a registered compiler. Read `.cache/compilers/<id>.json` directly.
- `triage.py is_internal_failure(text, rc, timed_out)` takes **text first**. Easy to call with
  `(rc, text)` by analogy with the run record, and it fails silently-ish when you do.
- On PowerShell, the agent-level `grep` tool silently returns nothing for paths under
  `.github/`. `Get-ChildItem -Recurse | Select-String` works. `Select-String` has no
  `-Recurse` of its own, and revision expressions like `13730886e^{commit}` must be quoted.
- `gh --jq` expressions need to be passed via a single-quoted variable, not inline.
