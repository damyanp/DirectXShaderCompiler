# Method observations from triaging #2792

Recorded here rather than fixed in place: a per-issue session does not write
shared state. Collation promotes what is worth promoting.

---

## 1. `classify`'s absence guard misses the most likely early failure — an ordinary diagnosed error

**Severity: real, would produce a wrong verdict. Demonstrated, not hypothetical.**

`classify` (`scripts/triage.py`) demotes a probe to `invalid-probe` in three
situations. The third is the absence guard:

```python
if verdict == "repro" and _is_absence_predicate(issue, match_file) \
        and (unsupported or is_internal_failure(text, rc, timed_out)):
```

`unsupported` means the output matched a **feature-absence marker**;
`is_internal_failure` means the probe crashed. **There is no third arm for "the
compile failed with an ordinary diagnostic".** On Windows that is E_FAIL
(0x80004005) with an `error:` line, which is neither of the two — so an
absence-shaped predicate scores such a probe as a textbook reproduction.

Measured, using real captured output from this issue
(`manual-case-classifier.txt`, section C; re-runnable with
`python data/issues/2792/classifier-probe.py`):

| input | what really happened | verdict under an unanchored absence predicate |
| --- | --- | --- |
| `variant-rs-register-mismatch-main-debug.txt` | dxc emitted 3 `error:` lines, exit 0x80004005, **no DXIL produced** | **`repro`** |
| `repro.hlsl:3:3: error: expected ')'` | rejected at parse | **`repro`** |
| `error: invalid profile ps_6_0` | marker present | `invalid-probe` ✔ |
| `Internal compiler error: access violation` (0xC0000005) | crashed | `invalid-probe` ✔ |

The first row is the dangerous one: the probe measured nothing, and it is scored
as the symptom being present.

SKILL.md currently describes the guard as covering this:

> The runner now reclassifies such a probe as `invalid-probe` when the compile
> also failed.

That overstates the code. It reclassifies when the compile failed **with a
marker or internally**. Suggested wording, if this is promoted: *"...when the
compile also tripped a feature-absence marker or failed internally. An ordinary
diagnosed error (E_FAIL plus an `error:` line) is neither, and still slips
through — so anchor the absence with a positive clause."*

**Why this class of issue is where it bites.** A missing-diagnostic issue is
about diagnostics, so its predicate necessarily talks about diagnostic text, and
"a compiler rejected the input with some *other* diagnostic" is by far the most
likely early-failure mode across a 20-release history. Feature-absence markers
and crashes are the two failure modes the guard was built from (#1877, #2202);
neither is the one this shape of issue actually meets.

**Mitigation, and it worked.** `match.json` here leads with a positive clause —
the disassembly must contain the out-of-bounds
`extractvalue %dx.types.CBufRet.f32 <val>, 1` — so no failed compile can satisfy
the predicate at all. Section E of the capture reruns the same four inputs
against the anchored predicate: none scores `repro`. **The anchor, not the
classifier, is what made this issue safe.** SKILL.md already advises it
("always confirm the probe actually emitted DXIL"), but nothing enforces or
checks it.

**Possible tooling change for collation to consider** (deliberately not made
here): when `_is_absence_predicate` is true and the predicate has **no**
positive clause, warn at capture time — the same way `run --args` without
`--label` now warns. That is cheap, and it turns a discipline into a check.

---

## 2. `_predicate_quotes` — the #3055 fix — is structurally unavailable to a missing-diagnostic issue

**Severity: latent here (no release triggers it), but a wrong verdict if it ever fires.**

`_predicate_quotes` suppresses a marker demotion when a *positive* clause of the
issue's own `match.json` quotes the matched marker verbatim. That fixes #3055,
where the issue's symptom **is** an existing diagnostic whose text can be written
into the predicate.

#2792 asks for a diagnostic that **does not exist in any DXC**. There is no text
to quote, so the suppression can never apply. Section D of the capture confirms
`_predicate_quotes` returns `False` for every marker.

The consequence is one-directional and only shows up on a *future* run: a release
that **fixes** this issue scores `no-repro` (correct), and is then demoted to
`invalid-probe` if its new diagnostic happens to contain a marker phrase.
Measured with a plausible gated wording (capture, section B):

```
  input   : "error: diagnosing a root constant overrun requires shader model 6.0 or above"
  verdict : invalid-probe
  reason  : output matched the feature-absence marker "requires shader model",
            so this build did not reach the code under test
```

`bisect` would trim away the release that fixed the issue — exactly the #3055
failure, with the #3055 remedy unreachable. Three other plausible wordings
(plain, validator-style, and one merely mentioning "the target profile") do
**not** trip a marker, so this is a hazard rather than a certainty. Nothing needs
changing today; whoever re-triages #2792 after a fix lands must check the header
before believing a `bisect` result.

SKILL.md's advice for diagnostic-quality issues — *"write the diagnostic text
into `match.json` rather than approximating it"* — is written for issues about a
diagnostic that exists. It should say what to do when the issue is that **no**
diagnostic exists: you cannot, so lead with a positive clause instead and expect
to re-check the classification after a fix.

---

## 3. Negative result, which the brief asked for explicitly: the rewritten classifier did **not** misbehave on this issue

Across 21 primary probes (ground truth + 20 releases) and 5 controls, **zero**
demotions fired, spuriously or otherwise, and every verdict matches what the
captured text shows by eye. `bisect` reported no skipped probes. Section A of the
capture re-scores five representative captures and agrees.

So the collision the brief warned about — the signal (`this build rejected the
input`) and the symptom (`an error message`) being the same observation — did not
materialise here, for a concrete reason worth recording: **the symptom of this
issue is the absence of *all* diagnostics, and the probes are clean exit-0
compiles.** There is no diagnostic text on a reproducing probe for a marker to
match. The #3055 collision needs the probe to *emit* something; a
missing-diagnostic issue's reproducing probes emit nothing.

That generalises: the classifier's exposure on a diagnostic-quality issue depends
on whether the *reproducing* case is noisy or silent, not on whether the issue is
"about diagnostics".

---

## 4. `fetch` reports "no code block" where the issue body *is* a runnable repro

#2792's body is 250 characters with no ``` fence, so anything keying off code
blocks reads it as prose. It is in fact a complete, compilable shader plus one
sentence of explanation, and it needed no reconstruction — repro quality is
`complete`, not `prose-only`.

Cheap and worth doing: the repro-quality rubric in SKILL.md and README.md could
say that `prose-only` means *no source was supplied*, not *no fenced block was
supplied*. Judging it from the rendered markdown alone marks a usable repro as
unusable, which is the direction that loses evidence.

---

## 5. `godbolt`'s one-line pane summary hid the whole finding, as SKILL.md predicts

`triage.py godbolt` printed:

```
  dxc_1_6_2112       exit=0  warning: DXIL.dll not found.  Resulting DXIL will not be signed for us
  dxc_trunk          exit=0  ;
  hlsl_clang_trunk   exit=0  clang: warning: argument unused during compilation: '
```

Not one of those three lines is about this issue. SKILL.md already warns about
this for `hlsl_clang_trunk` specifically ("Open the link"); it is not
Clang-specific — DXC's own first line is `;`, the first character of the
disassembly, and old DXC's is a CE environment warning. `manual-case-ce-panes.txt`
exists because of it.

That environment warning also caught a wrong claim in the first draft of
`godbolt-note.txt` ("no error, no warning"): the `dxc_1_6_2112` pane *does* emit a
warning, just not about the shader. Corrected before publishing. This is the
"`silently` is wrong the moment the compiler emits any warning at all" trap
arriving via the CE environment rather than the compiler.

---

## 6. A Clang *non*-error needs a control just as much as a Clang error does

SKILL.md step 7 says a Clang **error** is not evidence without a control, and
that was true here — `hlsl_clang_trunk` fails the pixel repro with `Unsupported
intrinsic llvm.dx.store.output.f32 for DXIL lowering`, and a one-line
`float main() : SV_Target { return 0; }` fails identically.

The converse needed a control too, and the rule is not written down. Clang
compiles the compute restatement cleanly and emits no diagnostic — which looks
like "Clang does not diagnose this either", a finding. Two further controls show
it is weaker than that:

- a syntactically broken root signature → `<source>:7:31: error: invalid
  parameter of RootSignature`, so Clang *does* parse and check root signatures;
- a root signature binding `b1` while the cbuffer sits at `b0` → **accepted**,
  where DXC reports `Shader CBV descriptor range ... is not fully bound in root
  signature`.

So Clang has no root-signature-vs-shader checking at all yet, and its silence on
the repro is "not implemented there either" rather than an independent judgement
that the shader is fine. Suggested addition to step 7: *"A clean Clang pane is
not evidence either. Before reporting 'Clang does not diagnose this', show Clang
diagnoses something in the same area — otherwise you have measured an
unimplemented feature, not an opinion."*

---

## 7. Cross-issue observation, deliberately left out of `comment.md`

Nothing in this issue points at another issue in this batch; I cannot see the
batch. One relationship is worth collation's attention: this is a **root
signature vs. shader** gap, and the mechanism it would live in
(`VerifyRootSignatureWithShaderPSV`, invoked from
`lib/DxilValidation/DxilContainerValidation.cpp`) is the same mechanism behind
any other issue about root signature/shader mismatches. If another issue in this
or a past batch concerns that verifier, the two share a root cause and probably a
fix. The draft says nothing about it.

---

## 8. Small note on `cmd-as-filed.txt`

Not written, deliberately: the issue supplies no command line at all, so
`cmd.txt` does not *depart* from anything filed. The profile `ps_6_0` is inferred
from `float main() : SV_Target` and is recorded in `expected.md` as an inference.
Worth a line in SKILL.md that `cmd-as-filed.txt` is for a **stated** command that
was changed, not for one that had to be supplied.
