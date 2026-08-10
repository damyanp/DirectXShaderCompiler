# Method notes — #3439

Findings about the triage method itself, from working this issue. Nothing here
is about DXC's behaviour; that is in `notes.md`.

## 1. A spelling-variant retry must key on anchor absence, not on the error text

`measure-link.py` probes very old releases, and v1.4.1907 rejects the `-Fo`
spelling this repro needs. My first version detected that by looking for
`Unknown argument` in the output and retrying with the alternate spelling.

That was wrong in a way that produced a *plausible* answer. v1.4.1907 sometimes
fails the same way **silently** — exit 1, empty output, no message to match — so
the retry never fired, the row was scored `invalid-probe`, and the matrix
reported 19/20. Re-keying the retry on **absence of the anchor** (retry whenever
the run did not produce the diagnostic we are trying to measure, whatever it
said or didn't say) recovered it: v1.4.1907 does reproduce, and the count is
20/20.

The general shape: a fallback that triggers on a *message* is a fallback that
silently gives up when the tool says nothing. Trigger on "I did not get the
observation I came for" instead. The failure mode is not a crash — it is a
confident, slightly-too-small number, which is the kind that survives review.

## 2. No release ships `dxl.exe`

Worth knowing before designing any linker measurement. Every release zip
contains `dxc.exe`, `dxv.exe`, `dxcompiler.dll`, `dxil.dll` — and no `dxl.exe`.
A linker sweep across releases therefore cannot be "run the release's linker".

The workable pattern (same one #3237 used) is to copy the *local* `dxc.exe` and
`dxl.exe` drivers beside each release's `dxcompiler.dll`, since Windows resolves
the DLL from the executable's own directory first. The drivers are thin; the
compiler and linker logic being measured is in the DLL.

That substitution needs a guard, or the sweep quietly measures the local build
N times and reports a beautifully consistent result. The guard is cheap: run
`dxc --version` in the staged directory and confirm it reports the *release*
version rather than the local build's marker; flag the row `SUBSTITUTION-WARNING`
if it does not. Any harness that does this substitution without the check should
not be believed.

## 3. Release trees live in two roots

Releases are under **both**:

- `<skill>/.cache/compilers/releases/<tag>/…` (17 tags), and
- `<repo>/build/tools/clang/test/dxc_releases/<tag>/<asset>/bin/x64/` — the
  seeded catalog, which is where v1.6.2112, v1.7.2308, v1.8.2502 and v1.8.2505.1
  live.

A harness that walks only the first root silently under-samples by four stable
releases and still prints a tidy summary. `triage.py` knows about both; anything
hand-rolled has to walk both too. Also, v1.4.1907 puts `dxcompiler.dll` at the
release root rather than under `bin/x64/`, so the layout is not uniform even
within one root.

## 4. Split the predicate so controls score the instrument, not the anchor

The full `match.json` here is `all_of[ diagnostic-anchor, mangling-regex ]`. That
is the right predicate for measuring the issue, but it makes controls
meaningless: `control-good.hlsl` fails clause 1 and returns `no-match`
regardless of whether clause 2 works at all. A control that passes for the wrong
reason is not a control.

The fix is a second predicate file (`match-mangled-function.json`) holding the
symptom clause alone, and running controls against that. Then `control-good`
returning `no-match` actually says "the mangling detector does not fire on clean
output", and `case-validator-payload` returning `no-match` actually says "the
detector distinguishes a readable name from a mangled one". Both are claims
worth having.

Cheap to do, and it is what let me report a *partial* result honestly instead of
a blanket one.

## 5. For an "output quality" issue, the control is a good message about the same subject

The temptation with a diagnostics-wording issue is to prove it by showing the
ugly message. That is not evidence of anything — every compiler has ugly
messages somewhere, and a reader can always say "so what".

What made this defensible was `control-redefinition.hlsl`: a diagnostic from the
same compiler, in the same run-shape, naming **the same function**, which comes
out as `error: redefinition of 'CallMeMaybe'`. Now the mangled message is not
"ugly", it is *inconsistent with the compiler's own behaviour three lines
earlier*. That reframes the report from taste to defect, and it cost one extra
file.

## 6. A cross-compiler *silence* needs a control just as much as an error does

SKILL.md warns that a Clang error is not evidence until you have a control,
because Clang's DXIL backend fails on unrelated inputs. The mirror image bit me
here: Clang **exits 0** on the repro and emits no diagnostic at all.

"The successor compiler doesn't have this problem" would have been a wrong and
quite attractive conclusion. The correct reading is that Clang does not report
the condition — but before claiming even that, I needed to rule out "Clang's
diagnostics don't surface in this CE mode". Running the redefinition control
through the same pane (it errors, exit 1) settled it.

Rule of thumb: if the observation is "the other compiler said nothing",
the control is "make the other compiler say something in the same
configuration". Otherwise you cannot distinguish *doesn't diagnose* from
*wasn't asked*.

## 7. The CE banner is compiled, so it must not assert what the panes disprove

Known hazard, but worth restating with a fresh instance. My first banner ended
with a line to the effect of "every pane is expected to fail". The Clang pane
exits 0, so the banner would have been telling a reader something the page
visibly contradicts — worse than saying nothing, because it is the first thing
they read.

The related trap is the token one: the banner is embedded into
`!dx.source.contents`, so any mangling-shaped token written into the prose
becomes a hit in the module. Verified after publishing by reading the shortlink
back through `/api/shortlinkinfo/<id>` and checking the stored source for `@@`.
That readback also confirms the per-pane arg overrides took, which the console
summary does not show — it echoes `cmd.txt` (`-T ps_6_0 -E main`) in the header
even when every pane actually ran `-T cs_6_0 -E main`.

## 8. Publishing a second CE link to capture a control

`triage.py godbolt` stores one link per issue, and `manual-case-godbolt-verify.txt`
is overwritten each run. To keep the Clang control as an artifact I ran the
control first, copied the verify file aside as
`manual-case-godbolt-clang-control.txt`, then re-ran the real publish so the
stored link and verify file are the primary ones. Both captures survive; the
issue's recorded link is the one that matters. Worked fine, no tooling change
needed — just do it in that order, because the second run clobbers the first.

## 9. `grep` (agent tool) returns nothing in this tree without a glob

Already documented in SKILL.md and confirmed again: the agent `grep` tool
silently returns zero matches across this repo unless a `glob` filter is given,
and it rejects subdirectory paths like `<repo>/lib` as non-existent. `git grep`
and `Select-String` were used throughout instead. Zero matches from that tool is
not a finding here.
