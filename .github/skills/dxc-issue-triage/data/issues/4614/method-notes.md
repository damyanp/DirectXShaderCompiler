# Method observations from #4614

For collation to weigh and promote (or discard). Nothing here edits `SKILL.md`
or `triage.py`.

---

## 1. A timed-out run records `# exit: 0`. Say so where predicates are chosen.

`out-v1.4.1907.txt` and the other 19 release captures read:

```
# exit: 0
# timed_out: 1
```

The `timeout` predicate keys on `timed_out`, so scoring is correct. But the
header, read by eye, says *the compiler exited successfully* — and any predicate
reasoning about exit status (`nonzero_exit`, or a hand-written "did it fail?"
check) scores an unbounded hang as a **clean successful compile**. That is the
fix-inventing direction.

SKILL.md's exit-code table is the natural home for this and currently has no
row for it. Suggested row: *hang / killed at TIMEOUT → recorded `exit: 0`,
`timed_out: 1` → internal failure? **only via the `timeout` predicate***.

This issue is the case where it bites hardest: 20 of 21 builds are in exactly
this state.

## 2. `cdb -p <pid> -c "kn"` samples the debugger's own thread, not the hung one.

Cost me one 5-minute run. Attaching to a live process creates an injected
break-in thread, and `kn` reports *that* thread:

```
00 ntdll!DbgBreakPoint
01 ntdll!DbgUiRemoteBreakin+0x4e
02 KERNEL32!BaseThreadInitThunk+0x17
03 ntdll!RtlUserThreadStart+0x2c
```

This is the worst possible failure shape: it is a plausible, complete,
successfully-captured stack that contains no error message and reads as "the
process is idle" — i.e. as evidence *against* a hang. `~*kn` (all threads) or
`~0s; kn` is required.

SKILL.md's crash-debugging box covers launching under `cdb` but not attaching
to something already running, which is the incantation a *hang* needs. Suggested
addition next to the existing four:

```bat
:: sample a HANGING process: attach, dump EVERY thread, detach without killing
cdb -p <pid> -c "~*kn 18; qd"
```

`qd` (quit-and-detach) matters too: a plain `q` kills the process, so you get
one sample rather than a series.

## 3. Two stack samples beat a longer timeout for proving a hang.

The natural move when 60 s is not convincing is to raise the timeout. It does
not actually answer the question — "no result in 300 s" is still not
"non-terminating", and each attempt is slow.

Sampling the same process twice is cheaper *and* stronger: at t=30 s and
t=90 s, 16 of 18 frames here were byte-identical **including their Child-SP
values**, with only a 62-byte return-address difference in the two innermost
frames. Fixed stack depth, cycling inside one function, for a minute. A slow
compile cannot look like that. Combined with reading the `NDEBUG` expansion of
the loop guard, that is a real proof of a spin rather than an appeal to
wall-clock.

Generalisable rule: **for a hang, measure the stack twice; for a crash,
measure it once.**

## 4. The `NDEBUG` discriminator has a third outcome, and it is the interesting one.

SKILL.md gives two: an assert-only defect that is "silent by construction" in
release builds (#2191), and an assert whose unchecked value goes on to crash
anyway (#3259). #4614 is a third: the unchecked value goes on to **spin**.
Same discriminator procedure, but the release symptom is neither silence nor a
crash — and it is *worse* than the assert, since the user gets no diagnostic
and no exit at all.

Worth naming in the same paragraph, because "the release build does not crash"
is otherwise easy to file under "silent by construction" and stop looking.

There is a nice second-order detail here: continuing past the first assert with
`gh` landed directly on DXC's *own* infinite-loop detector
(`"Infinite loop while SROA'ing value, use isn't getting eliminated."`). When a
codebase has already instrumented the failure you are trying to characterise,
`gh` finds that instrumentation for you. Worth mentioning as a reason to run the
`gh` continuation even when the first assert already looks conclusive.

## 5. A composed predicate can be self-protecting against `invalid-probe`.

Both clauses (`timeout`, `internal_failure`) are unreachable by a release that
rejects the shader before running the pass — such a release exits E_FAIL fast
with a diagnostic and satisfies neither. So a `repro` verdict here *cannot* be
a feature-absence artefact, and the usual per-release feature-presence control
was not load-bearing.

The mirror of SKILL.md's absence-predicate warning, and worth stating as such:
absence predicates are satisfied for free by a failed compile, while
**crash/hang predicates are falsified for free by one**. The second direction
loses evidence rather than inventing it, which is safer but still worth knowing
when deciding how much control work an issue needs.

## 6. `re.findall` over a fetched issue body needs the CRLF normalised first.

`issue.json` bodies use `\r\n`. A fence pattern written as ```` ```[a-z]*\n ````
finds **zero** blocks and the fidelity check then reports the repro as
*differing* from the issue body — a confident false mismatch from a regex bug,
in a check whose whole purpose is to be trusted. Caught only because "0 fenced
code blocks" was printed next to the result; the generator now hard-errors
instead of reporting a mismatch it cannot substantiate.

Same family as SKILL.md's "a negative result from a command that errored is not
a negative result". Cheap general guard for any generator: make it **fail**
rather than emit a negative when its own input extraction comes back empty.

## 7. Small `triage.py` friction

- `triage.py sql` is the obvious way to look up a release's `cached_path`, but a
  generator wanting the same thing has to reach for `triage.con()`; there is no
  `triage.db()` despite `DB` existing as a module global, which is an easy
  wrong guess (I made it). A tiny documented accessor, or a mention of `con()`
  in the harness guidance, would save the round trip.
- Wall-clock note for scheduling, not a defect: `TIMEOUT = 60` means a
  `--linear` scan of an always-hanging issue costs 20 minutes of pure timeout.
  Worth expecting rather than fixing.

## 8. `git tag --contains` is an eyeball answer; `--is-ancestor` over the scan's own tag list is a measured one.

To place a fix commit in release history I first read `git tag --contains
527d58e5a` and picked the earliest-looking release off it. That output is
unordered for this purpose and mixes in non-release tags, so "earliest" was my
judgement, not the tool's — on a question that the whole history verdict then
rested on.

Replacing it with `git merge-base --is-ancestor <sha> <tag>` run over **the
same ordered tag list the bisect used** is strictly better, and not only
because SKILL.md asks for `--is-ancestor` before naming a SHA:

- the boundary falls out of the sequence instead of being read off a list;
- the tags are exactly the ones with `out-<tag>.txt` captures, so the ancestry
  result can be joined to the measurements without a second mapping step;
- both answers get recorded. Three tags answer "not contained" and seventeen
  answer "contained" — which is what shows the test discriminates. An
  ancestry check that returns the same value everywhere proves nothing, and
  you cannot tell the difference from output that only lists the hits.

Cheap generalisation, same family as note 6: **when a check is load-bearing,
record the negative cases too, not just the positive ones.**

## 9. Cross-issue observation, deliberately left out of the draft

Per the brief, cross-issue claims are collation's. Noting here only that this
issue's history is entangled with a **closed** issue (#3016) and the commit
that closed it, and that the finding — the guarding regression test does not
exercise the reported construct — is the kind of thing worth checking for on
any issue whose thread says a predecessor was fixed. The draft states this in
terms of measured release behaviour rather than as a claim about another
issue's status.
