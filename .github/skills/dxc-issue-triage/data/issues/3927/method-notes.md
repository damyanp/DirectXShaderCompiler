# Method observations from #3927 (for collation to promote or discard)

## 1. `godbolt-note.txt` is compiled into SPIR-V too — via `OpSource`, not `!dx.source.contents`

`SKILL.md` records this for DXIL: the banner is prepended to the source CE builds, and DXC
records its input in `!dx.source.contents`, so literal IR quoted in a note appears in the
pane's own output. **The SPIR-V panes have the same defect through a different instruction.**
CE's DXC builds emit `OpSource HLSL 600 %4 "<the entire shader>"`, so the banner is quoted
back verbatim near the top of every pane.

It bit twice here, and the second bite is the interesting one:

1. First draft claimed "`Tex1` and `SS1` … no decoration or variable for either appears
   anywhere". A reader doing the obvious Ctrl-F finds `Tex1` — in the embedded source, where
   the shader declares it. The claim is true of the module and false of the pane text.
2. So the note was rewritten to say "search the output for `%Tex1`". Measured after
   publishing: **`%Tex1` appeared 4 times in the panes** — twice per pane, in the embedded
   copy of the sentence telling the reader to search for it. A "what to look for" note that
   names its own search string guarantees a false positive for that string.

The rule that survives both: **a `godbolt-note.txt` must not contain any token a reader would
search for.** Describe the location structurally ("the decoration block near the top of each
pane; of the four resources declared, only the first pair is decorated there") rather than
naming an identifier. The final note contains zero occurrences of `Tex0`, `Tex1` or `%Tex1`,
and the panes contain 10 `%Tex0` and 0 `%Tex1` — all module content.

Cheap mechanical check, worth adding to `godbolt` or to the skill: after publishing, count
occurrences of each note token in `manual-case-godbolt-verify.txt`. It is a two-line check
and it caught a live error.

## 2. The SPIR-V floor is two releases deep, not one, and both need the same control

`SKILL.md` names v1.4.1907 as answering `SPIR-V CodeGen not available`. **v1.5.2003 does the
same**, but it is a prerelease and is outside the stable history population unless an issue
explicitly names it. `bisect` must still list the skipped prerelease so nobody mistakes
"not visited" for "passed"; it must not add it to the invalid count for this issue.

Measured exit status on both (x64 `dxc.exe`): **exit 1**, stderr
`dxc failed : SPIR-V CodeGen not available. Please recompile with -DENABLE_SPIRV_CODEGEN=ON.`
Not `0x80070057`. The `CodeGen not available` marker in `classify` catches both cleanly, so
the classification is right; only the *count* under-reports.

The durable wording is therefore: v1.4.1907 is the stable SPIR-V floor; v1.5.2003 is a known
prerelease without the backend and is named in the skipped-release report. This issue does
not qualify for the carve-out, so its existing hand-run is corroboration only; a prerelease
enters formal history only when the filing names it and `release-policy.json` opts in.

## 3. For a report that quotes compiler output, diff it against the release it names

The strongest fidelity evidence available on this issue cost about 40 lines of Python:
`check-report-fidelity.py` pulls the disassembly out of `issue.json`'s body and compares it
against the capture from the release the reporter named (`dxc_2021_07_01` → v1.6.2106). It
came out **identical line for line, 64 lines**. That upgrades the repro from "a shader that
shows the symptom" to "the reporter's instance", and it is mechanically re-checkable rather
than an assertion.

This generalises to any issue whose body pastes DXIL, SPIR-V or a diagnostic: the issue body
is already committed evidence in `issue.json`, and the matching release capture is already
being taken by `bisect`. Worth doing whenever a report quotes output and names a version.

## 4. Measure a command-line deviation instead of asserting it is inert

`cmd.txt` had to drop the reporter's `-Fo test.spv` so the predicate could read the module.
"`-Fo` only selects the output sink" is obviously true and was still worth proving:
`check-fo-equivalence.py` parses the `.spv` binary directly (no `spirv-dis` is built in this
tree) and checks the bound and the `Binding`/`DescriptorSet` decorations against the stdout
disassembly. This is the same discipline `SKILL.md` already demands for a CE fold — "run the
transformation on a case that is known-good and confirm it still passes" — applied to the
smaller, more frequent case of a flag change in `cmd.txt`.

## 5. A content predicate needs its anchor for the *opposite* reason an absence predicate does

`SKILL.md` explains at length that an absence predicate is satisfied for free by a compile
that never started. The mirror is quieter: a **presence** predicate is *falsified* for free by
the same compile, and a false `no-repro` at the old end of a scan reads as "this used to work"
— the direction that invents a fix. Here that would have been a fabricated regression at
v1.5.2010 and a published claim that no release ever eliminated these bindings. The
`OpEntryPoint` anchor does not prevent that (the symptom clauses already fail); what prevents
it is `classify`'s feature-absence marker plus the `control-hello` capture proving *why* the
probe was invalid. Worth stating in the skill that presence predicates fail in the
fix-inventing direction, so a SPIR-V or DXIL-content issue needs the backend-presence control
even though nothing in the predicate looks absence-shaped.

## 6. `git rev-parse --verify --quiet <sha>^{commit}` needs quoting in PowerShell

Unquoted, `13730886e^{commit}` silently resolves to nothing and the command exits non-zero,
which reads exactly like "this commit does not exist" — the `SKILL.md` "a negative result
from a command that errored is not a negative result" trap, in a new costume. It briefly
looked as though *both* the build SHA and the cited upstream SHA were unresolvable. Quoted
(`git rev-parse --verify --quiet "13730886e^{commit}"`), both resolve.

Re-verified the provenance with the required control while there:
`git diff --name-only ab5400907 13730886e` → **0** files outside the skill directory;
control against `13730886e~200` → **581**. The query can detect differences, and finds none.
