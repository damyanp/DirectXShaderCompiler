# Method observations from triaging #3092

For collation to promote (or reject). Not edits to `SKILL.md` — this is a per-issue session.

## 1. A text-absence predicate can be defeated by the compiler quoting the symbol back

**Where:** `variant-execmodeid-default-env-main-debug--match-no-spec-link.txt`.

`match-no-spec-link.json` is `not_regex "LocalSizeId|BuiltIn WorkgroupSize"` — "the module does
not tie the workgroup size to a spec constant". SKILL.md already warns that an absence
predicate is satisfied *for free* by a compile that never started. This is the **opposite**
failure and I have not seen it written down: an absence predicate can be **falsified for free**
by a compile that failed, because DXC's SPIR-V validation echoes the rejected instruction into
the diagnostic:

```
fatal error: generated SPIR-V is invalid: 2nd operand of ExecutionModeId: operand
  LocalSizeId(38) requires SPIR-V version 1.2 or later
  OpExecutionModeId %main LocalSizeId %TGSIZE_X %uint_1 %uint_1
```

The predicate is scored over combined stdout+stderr, so `LocalSizeId` is present, so the
predicate does not match — reporting "this build linked the workgroup size to the spec
constant" about a build that emitted nothing at all.

I declared that control `--expect match` and the runner caught it:
`WARNING: control expected match but scored no-repro`. Without the control it would have
passed silently.

Two things worth noting for the method:

* **Tightening the regex does not fix it.** The obvious repair — anchor on
  `OpExecutionModeId\s+%\w+\s+LocalSizeId` instead of the bare word — fails too, because the
  validator prints the offending instruction *verbatim* on the next line. Any pattern precise
  enough to match the real instruction also matches the diagnostic quoting it.
* **The general shape:** wherever a compiler's diagnostics quote IR back at you (SPIR-V
  validation, `llvm_unreachable` messages, verifier failures), the output stream is not a
  reliable witness to what was *emitted*. If an absence clause names an IR construct, either
  score it against the artifact rather than the console, or pair it with a positive clause that
  a failed compile cannot produce. SKILL.md's existing advice ("anchor with a positive clause")
  happens to fix this too, so the addition is really to the *reason* it is given: the anchor
  protects against false matches **and** false non-matches.

I did not change the predicate, because for this issue's repro the primary evidence is
`match.json` (anchored on the diagnostic) and every release capture was read by hand. The
hazard is documented in the predicate's own `note`.

## 2. `--expect match` earned its keep on a control nobody would have doubted

SKILL.md says the `--expect` check "runs in both directions, and both are real", citing #1803's
identity control. This is a second, different instance: I expected `match` because a failed
compile obviously cannot emit `LocalSizeId`, and I was wrong for a reason I would not have
guessed. The lesson is narrower than "declare `--expect`" — it is that the controls **least
likely to teach you anything** are worth declaring, because a control whose outcome is obvious
is exactly the one where a surprise means the predicate is wrong rather than the compiler.

## 3. For a capability request, the CE Clang pane can be the finding, not a footnote

SKILL.md's #1627 note says a comparison pane can create something worth seeing where there was
nothing, and warns that the *first line* of a `hlsl_clang_trunk` pane is usually a
`-Qembed_debug` unused-argument warning, so `godbolt`'s summary can print nothing of the
finding. Both fired here, in the same run:

```
  hlsl_clang_trunk   exit=1  clang: warning: argument unused during compilation: '
```

That summary line says nothing. The pane's *second* line is
`error: 'numthreads' attribute requires an integer constant` — Clang reproducing DXC's
diagnostic word for word, which on a five-year-old feature request is arguably the most useful
single fact available: the gap will exist in the successor front end too, so it is worth
specifying once. Restating the existing rule with teeth: **on any issue where a Clang pane is
included, fetch the pane's full output rather than reading `godbolt`'s summary line.**

The controls SKILL.md demands were run and captured (`manual-case-clang-panes.txt`): Clang
compiles the same shader with a `static const` group size, and compiles a shader that declares
and uses the same `[[vk::constant_id]]` constant. So the failure is specific, not backend noise.
`-fsyntax-only` was not needed — the front end hard-errors, so the backend never runs, which is
the rule SKILL.md already gives for #3055.

## 4. `triage.py run` cannot drive Compiler Explorer, so cross-compiler controls need a script

`run --shader X --label Y --expect` exists so that capturing a control is easier than not
capturing it — but it only drives locally registered compilers. A Clang control lives on CE,
where the only supported entry point is `godbolt`, which publishes exactly one source. I wrote
`ce-probe.py` in the issue directory (it imports `triage.ce_compile`) so the Clang controls are
re-runnable rather than hand-quoted, and captured them as `manual-case-clang-panes.txt`.

If cross-compiler controls become common, `run --compiler ce:<id>` would remove the need for
each worker to reinvent this — and, more importantly, would put CE controls under `reindex`'s
`--expect` re-checking, which a `manual-case-*.txt` file is not.

## 5. The SPIR-V floor is v1.5.2010, and for this issue it postdates the report

The brief warned that v1.4.1907 answers `SPIR-V CodeGen not available`; it did, and `classify`
demoted it correctly with `# invalid-probe-reason:`. Worth adding to SKILL.md's floor
paragraph: **the effective SPIR-V floor is v1.5.2010 (2020-10-22)**, since v1.5.2003 carries no
usable `dxc` asset either. #3092 was filed 2020-08-19, so the oldest probeable release is two
months *younger* than the report — "always reproduced" here cannot cover the reporter's own
build, and the write-up has to say so.
