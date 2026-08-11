# Issue 4615 — DXIL debug locations do not respect `#line` directives

Filed 2022-08-24 by `maoenpei` (NVIDIA Nsight Graphics). No labels. Prose only, no repro,
no attached shader. Blames PR #2991.

**Verdict: reproduces on `main` (dxc 1.9.0.5433, public commit `13730886e`), and has since
v1.5.2010. It is deliberate**, per the maintainer reply on the thread and per the change that
introduced it, which also landed a test locking the behaviour in. The reporter accepted the
default in the thread and narrowed the ask to an **opt-in flag**, which does not exist. So the
live item is an enhancement, not a defect.

---

## 1. Ground truth

| | |
|---|---|
| compiler id | `main-debug` |
| `dxc --version` | `dxcompiler.dll: 1.10(5433-ab540090)(1.9.0.5433) - 1.9.0.5433 (triage, ab5400907)` |
| citable commit | **`13730886e`** |

The binary self-reports `ab5400907`; the citable public commit is `13730886e`. Checked rather
than assumed:

- `git diff --name-only ab5400907 13730886e` → **0** files outside `.github/skills/dxc-issue-triage/`.
- CONTROL, `git diff --name-only ab5400907 13730886e~200` → **581** files outside it.

So the two trees are identical for all compiler source, and the control shows the comparison can
fail. Everything below that says "main" was produced by that build.

## 2. Repro (agent-constructed — the issue supplies none)

`repro.hlsl`, 10 lines. **Physical line numbers are load-bearing; do not reflow it.**

```hlsl
float4 main(float2 uv : TEXCOORD0) : SV_Target {   // line 6
  float4 before = g_tex.Sample(g_smp, uv);         // line 7   <- BEFORE the directive
#line 400 "virtual-source.hlsl"                    // line 8
  return before * 2.0f;                            // line 9   <- AFTER the directive
}                                                  // line 10
```

`cmd.txt`: `-T ps_6_0 -E main -Zi -Qembed_debug repro.hlsl`

Exactly one statement each side of the directive. The first draft had two statements after it and
the optimiser folded one away, which would have made the capture depend on optimisation level;
that draft was discarded.

### Predicate (`match.json`) — `all_of`, two presence clauses and two absence clauses

1. `!DILocation\(line: 7,` — **self-test.** The `Sample` call is before the directive, so it is
   line 7 under *both* behaviours. This clause fails if the module carries no debug locations at
   all, or spells them differently.
2. `!DILocation\(line: 9,` — the symptom stated as a **presence**: the physical line survives.
3. `not_regex !DILocation\(line: 40[01],`
4. `not_regex !DIFile\(filename: "virtual-source\.hlsl"`

Clauses 3-4 alone would be an unanchored absence predicate — satisfied by any failure to emit
debug info. Clauses 1-2 are what stop that. See §7.

## 3. What main does

`out-main-debug.txt`, exit 0:

```llvm
!1  = !DIFile(filename: "repro.hlsl", directory: "")
!68 = !DILocation(line: 7, column: 10, scope: !4)
!69 = !DILocation(line: 9, column: 17, scope: !4)
!70 = !DILocation(line: 9, column: 3, scope: !4)
```

Physical lines throughout; one `!DIFile`, the physical file. No `line: 400`, no virtual
`!DIFile`. The reported symptom, exactly.

## 4. History — 20 stable releases, linear scan

`bisect --linear`, one capture per release (`out-v*.txt`), summarised in
`manual-case-release-matrix.txt`.

- **v1.4.1907 (2019-07-15) — `no-repro`.** It honours `#line`:
  ```llvm
  !70 = !DILocation(line: 400, column: 17, scope: !71)
  !72 = !DIFile(filename: "virtual-source.hlsl", directory: "")
  ```
- **v1.5.2010 (2020-10-22) through v1.9.2607 (2026-07-29) — `repro`, 19 releases.**

One transition, at v1.5.2010. (The linear scan prints "non-monotonic history … transitions at
v1.5.2010 -> repro"; that is the scan's phrasing for any transition, not a second window.)
5 prereleases excluded by policy; v1.2.0-alpha has no usable dxc asset. No `release-policy.json`
— the issue names no prerelease.

**The issue's dating is one release off.** It says "after dxc validator version >= 1.6"; the
change is already present in v1.5.2010, ten months before v1.6.2104. Not staleness — the
behavioural description is accurate today — but worth stating if anyone dates the change from
the issue text.

### Attribution — PR #2991 / `bce85df11`, strong but not proven

The reporter's blame is correct.

- `git merge-base --is-ancestor bce85df11 v1.5.2010` → 0 (yes); against `v1.4.1907` → 1 (no).
  So the commit is inside the window the measurement isolates.
- The window v1.4.1907..v1.5.2010 holds **434** commits. **3** touch
  `tools/clang/lib/CodeGen/CGDebugInfo.cpp`: `29759a894` (a `StringRef` warning fix),
  `ce645d1c1` (main-file-name handling), and `bce85df11`. Only `bce85df11` touches the
  `getPresumedLoc` call sites, adding `/*UseLineDirectives*/ false` at four of them.
- Those four sites are still on `main`: `CGDebugInfo.cpp` lines 125, 247, 278, 291, each marked
  `// HLSL Change`.
- PR #2991 also added `tools/clang/test/HLSLFileCheck/dxil/debug/pound_line.hlsl`, which asserts
  the *new* behaviour with `CHECK-NOT`s. The behaviour is tested, not incidental.

Not built at `bce85df11`, so this is strong attribution, not proof.

## 5. The rest of the thread's claims, each measured

Maintainer `adam-yang` (2022-08-31) answered that this is intentional, that debug info points at
the PDB's files rather than `#line`, and that `#line` *is* respected for error messages. Both
halves check out, and one more contrast was worth having.

**B. Diagnostics honour `#line`** — `variant-diag-main-debug.txt` (`control-diag.hlsl`, a
deliberate error one line after the directive):

```
virtual-source.hlsl:400:17: error: invalid format for vector swizzle 'no_such_member'
```

**C. The SPIR-V back end honours `#line`** — `variant-spirv-main-debug.txt`
(`-spirv -fspv-debug=line`):

```
%5 = OpString "virtual-source.hlsl"
OpLine %5 400 17
```

So within one compiler, on one source file, three consumers disagree: diagnostics and SPIR-V take
the virtual location, DXIL takes the physical one.

**D. There is no opt-in flag** — the whole point of the reporter's follow-up. Searched the option
table and the full `--help`. The only `#line` compile option is `-ignore-line-directives`
(`HLSLOptions.td:313`), and it goes the *opposite* way: with it the diagnostic above moves to
`control-diag.hlsl:9:17` (`variant-diag-ignorelinedirectives-main-debug.txt`) while DXIL locations
stay physical (`variant-ignorelinedirectives-main-debug.txt`, still `repro`). `-line-directive`
(`HLSLOptions.td:611`) is `Flags<[RewriteOption]>` — rewriter only, not a compile option.
No `-Zi`/`-Zs`/`-Fd`/`-fspv-debug` variant offers the behaviour either.

**E. `hlsl_clang_trunk` already honours `#line`** (`manual-case-clang-probe.txt`, and pane 4 of
the Compiler Explorer link). On the identical compute restating, the Clang-based front end emits

```llvm
!DIFile(filename: "virtual-source.hlsl", directory: "/app")
!DILocation(line: 400, ...)
```

while `dxc_trunk` on the same source, run as the control in the same capture, emits physical
`line: 9`. This is a finding about where the behaviour is heading, not a claim about a shipped
product.

## 6. Controls

Every control was declared with `--expect` before it ran, and every one came back as declared.

| control | why | expected | got |
|---|---|---|---|
| `control-echo.hlsl` — `#line` text only inside a comment | `!dx.source.contents` embeds the whole source, so the literal `#line 400 "virtual-source.hlsl"` is present in *every* capture. A bare-token search for `400` or the filename would be falsified by the echo. | match | match |
| `control-physical400.hlsl` — 401 lines, `return` genuinely on physical line 400, no `#line` | proves clause 3 is falsifiable **on main itself**, not only on a 2019 release | no-match | no-match |
| `control-diag.hlsl` | claim B | no-match | no-match |
| `-spirv -fspv-debug=line` | claim C | no-match | no-match |
| no `-Zi` | the absence trap, §7 | no-match | no-match |
| `-ignore-line-directives` | claim D | match | match |
| `-ignore-line-directives` + `control-diag.hlsl` | claim D | no-match | no-match |
| compute restating (`compute-restating.hlsl`) | not stage-specific; also the CE vehicle | match | match |

## 7. The absence trap, and how it was closed

An absence predicate over debug metadata is satisfied by the *failure* to emit debug metadata. A
dropped `-Zi` produces a module with no `!DILocation` at all, which contains no `line: 400` and no
virtual `!DIFile` — and would score `repro` on every release ever built.

Three separate things close it.

**(a) The predicate carries its own self-test.** Clause 1 requires `!DILocation(line: 7,` to be
*present*. `variant-nodebuginfo-main-debug.txt` (same command, `-Zi`/`-Qembed_debug` removed) is
the live demonstration: no debug locations, self-test **fails**, verdict `no-repro`. A module
without debug info cannot masquerade as a reproduction.

**(b) The self-test was scored on every release, in the same capture the predicate scored.**
`manual-case-release-matrix.txt` prints, per release, the verdict, the self-test result, the
`!DILocation` line numbers and the `!DIFile` names. All 19 `repro` releases **PASS** the
self-test; so does the one `no-repro` release. This also disposes of the
formatting-drift hazard: had a release spelled these nodes differently, its self-test would have
failed rather than silently flipping the verdict, and the line/file columns would show what it
printed instead. It did not happen — the spellings are stable across the whole 2019-2026 range.

**(c) The flags were proved to be parsed, not merely accepted** (`manual-case-flag-provenance.txt`):

- `-Zi` is load-bearing: dropping it removes `!DILocation` entirely.
- `/ZZZNONSENSE` **exits 0** and produces byte-identical stdout (sha256/16 `b362a07f74efdc25`).
  A clean exit proves nothing about a `/`-style flag.
- `-Qembed_debugZZZ` exits **1**, `Unknown argument`. So the `-` parser *does* reject unknowns,
  which is what proves `-Qembed_debug` was parsed.
- `-Fd no-such-directory\` exits **1**, "The system cannot find the path specified" — a flag made
  to fail on purpose.
- Incidentally: `-Qembed_debug` does not change the stdout disassembly at all (identical hash).
  `-Zi` alone is what puts `!DILocation` on stdout; `-Qembed_debug` only silences the warning and
  affects the container.

## 8. Path sensitivity

`#line` names a file path and the capture echoes source, so this issue is unusually able to leak a
machine path. The virtual filename is deliberately relative and neutral (`virtual-source.hlsl`),
the physical file is `repro.hlsl` in the issue directory, and `!DIFile(... directory: "")` comes
back empty. Every generator (`gen-control-physical400.py`, `flag-provenance.py`,
`release-matrix.py`, `clang-probe.py`) imports `triage` and pipes its own output through
`redact_paths()`; nothing was hand-edited. `check_paths.py --issue 4615` is clean.

## 9. Compiler Explorer

<https://godbolt.org/z/fdMjWcKd1> — four panes on one compute restating:

1. `dxc_1_6_2112` `-T cs_6_0 -E main -Zi -Qembed_debug` — physical lines
2. `dxc_trunk` same — physical lines
3. `dxc_trunk` `-spirv -fspv-debug=line` — `OpLine %4 400 18`, virtual
4. `hlsl_clang_trunk` `-T cs_6_0 -E main -Zi` — `!DILocation(line: 400)`, virtual

Read back from the shortlink and stored in full in `manual-case-godbolt-verify.txt`.
**CE prepends a banner, which shifts every physical line by +24 in this link** (7→31, 9→33), so
the pane shows `line: 31`/`line: 33` where local output shows 7/9. That is the CE editor's
numbering, not a behaviour difference — and on a `#line` issue it is exactly the kind of detail a
reader could misread, so `godbolt-note.txt` says so. An earlier 3-pane pixel-shader link
(`https://godbolt.org/z/EYThK7jso`, shift +20) is superseded and should not be cited.

## 10. Cross-reference (for collation, not for the comment)

**#8679** "Standardize `#line` handling in dxcompiler" (2026-07-27, `hbystuff`, labels `bug` +
`needs-triage`) is a successor request from the same vendor. It cites #4615 explicitly and asks
for the same two things the 2022 thread converged on: an opt-in flag near-term, and standard
`#line` semantics in the Clang modernization work. It appears in #4615's timeline as a
cross-reference. Per the method, cross-issue claims belong to collation, so `comment.md` says
nothing about it — but the relationship matters: **#4615 is the original and #8679 the successor**,
and finding E above (Clang already honours `#line`) is directly relevant to #8679's second ask.

## 11. Assessment

- **Status: repros.** Confirmed on `main` and on 19 of 20 stable releases.
- **History: regressed-in v1.5.2010** — deliberately, by PR #2991 / `bce85df11`.
- **Confidence: high.** Symptom, mechanism, boundary, and the maintainer's stated intent all
  agree; the source change is still present and still tested.
- **Suggested action: `enhancement-not-bug`.** Nothing here is broken by the project's own
  definition: the current behaviour was chosen, is documented in the thread, and is under test.
  The reporter agreed to keep it as the default. What remains is a feature request for an opt-in
  flag, and whether to add one is a maintainer call — the comment does not pre-empt it.
- **Labels** (issue has none): add `debug info` — this is debug-info generation; and
  `enhancement` — the live ask is a new opt-in flag, not a defect. Not proposing `spirv` (SPIR-V
  is the contrast, not the subject) or `check-in-clang` (that label asks for a Clang comparison;
  it has already been run, §5E).
