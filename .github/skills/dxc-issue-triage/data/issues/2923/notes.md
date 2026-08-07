# #2923 — triage notes

**Issue:** [Structs passed to subroutines (can) cause the numbering pass to get
confused about offsets of members](https://github.com/microsoft/DirectXShaderCompiler/issues/2923)
— filed 2020-05-27 by @jeffnn, open, unlabelled, assigned to @jeffnn.
One comment, @damyanp 2024-06-27: *"@jeffnn - is this something we still need to
track?"* — never answered.

**Verdict:** `repros` on current `main` (`main-debug`, `ab5400907`,
`1.9.0.5433`), with an important qualification about history (below).

---

## 1. What had to be built, and why

The issue names no shader and no command line. It says: edit
`PixStructAnnotation_SequentialFloatN` in `pixtest.cpp` so the payload struct is
passed to a subroutine that calls `DispatchMesh`, and run the unit test.

Modifying the unit test is off limits here (the compiler is measured as it is),
and the symptom is invisible to `dxc`: `-dxil-annotate-with-virtual-regs` is a
PIX-only pass that never runs during ordinary compilation. So the repro is the
pipeline the test itself performs (`PixTestUtils.cpp:244`), driven from the
command line:

```
dxc   -T as_6_5 -E main {-Od|-O1} -HV 2018 -enable-16bit-types -Zi -Qembed_debug
dxa   -extractpart=dbgmodule                      # the ILDB debug module
dxopt -opt-mod-passes -dxil-dbg-value-to-dbg-declare -dxil-annotate-with-virtual-regs
opt   -S                                          # readable annotated IR
```

`run-2923.cmd` is that pipeline plus `check-2923.py`, which reads the resulting
`!pix-alloca-reg` / `!pix-alloca-reg-write` metadata and reports it. It is
registered as the compiler id `main-debug-pix` so `triage.py run` can score it
(see `method-notes.md`).

`opt.exe` from this build does **not** have the PIX passes linked, even though
`tools/clang/test/HLSLFileCheck/pix/*.hlsl` invoke them as `%opt -S
-dxil-annotate-with-virtual-regs`. `dxopt.exe` does, because it loads them out
of `dxcompiler.dll`.

## 2. What the compiler does today

`repro.hlsl` at `-Od`, on `main-debug` (`out-main-debug-pix.txt`, and the raw
IR in `repro-Od.annotated.ll`):

```
  %0     [1 x float]                  regs[0] base=0 count=1
         declares: p [DW_TAG_auto_variable src-line 19] !DIExpression(DW_OP_bit_piece, 0, 32)
         writes  -> registers: (none)
  ... %1..%5, bit_piece 32/64/96/128/160, all unwritten ...
  %6     %struct.smallPayload.0       regs[6..11] base=6 count=6
         declares: p [DW_TAG_arg_variable src-line 16] !DIExpression()
         writes  -> registers: 6,7,8,9,10,11

  var !47 "p" [DW_TAG_auto_variable src-line 19]: 6 alloca range(s), declared registers [0, 1, 2, 3, 4, 5], written registers []
         registers declared but NEVER written: [0, 1, 2, 3, 4, 5]
  var !99 "p" [DW_TAG_arg_variable src-line 16]: 1 alloca range(s), declared registers [6..11], written registers [6..11]
```

`main`'s local `p` is described, member by member, by six PIX virtual registers
0..5 at bit offsets 0/32/64/96/128/160 — and **not one of those six registers is
ever written**. All six member writes were numbered onto registers 6..11, which
belong to the copy the inlined subroutine took.

The two variables are both spelled `p`, so the checker resolves the
`DILocalVariable` rather than trusting the name: the unwritten one is
`DW_TAG_auto_variable` at **source line 19** (`main`'s local), and the written
one is `DW_TAG_arg_variable` at **source line 16** (`Sub`'s parameter). That
distinction is the whole finding, and it is the same at `-O1`, where the ranges
swap — `main`'s `p` takes registers 6..11 and the callee's copy takes 0..5 —
but it is again the **caller's** variable that receives no writes
(`variant-o1-main-debug-pix.txt`). So a PIX user stopped anywhere in `main`
cannot read `p` at either optimisation level; only the register numbers differ.

At `-O1` there is additionally a 13th alloca (`%12`, registers 12..17) carrying
the six writes that actually feed `DispatchMesh`, with no `dbg.declare` at all.

The verbatim unit-test shader (`control-no-subroutine.hlsl`) is numbered
correctly at both `-Od` and `-O1`: one variable, registers 0..5, all written
(`variant-control-verbatim-test-*.txt`).

`control-inout-param.hlsl` is `repro.hlsl` with one word added — the subroutine
takes the payload `inout`, so no copy is made — and it is also numbered
correctly at both optimisation levels
(`variant-control-inout-*.txt`). **The by-value struct copy is the trigger, not
the subroutine call.**

`check-2923.py` also emulates the assertions
`PixStructAnnotation_SequentialFloatN` makes. On `repro.hlsl` at `-Od`:

```
  OffsetAndSizes.size() : expected 1   actual 7   FAIL
  ValidateAllocaWrite(0): expected regBase+index == 0, actual 6+0 == 6 FAIL
  ... (1..5 likewise, 7..11) ...
```

so the edit the issue asks for does still make the named test fail.

## 3. Reconciling this with `expected.md`

`expected.md` was written before anything ran, and its criteria (1) and (2) are
**not** what happened, so this has to be said plainly rather than smoothed over:

* criterion (1) — "the payload alloca's `!pix-alloca-reg` count is not 6" —
  **false**. The count is 6.
* criterion (2) — "the six member stores do not carry `!pix-alloca-reg-write`
  offsets that form the distinct run 0..5 **relative to the alloca base**" —
  **false as worded**. Relative to *their* alloca's base they are exactly 0..5.
* criterion (3) — assert or crash — **false**. Nothing crashes; every stage
  exits 0.

The wording "relative to the alloca base" was the mistake. The quantity PIX and
the unit test actually consume is the **absolute** register, `regBase + index`
(`PixTest.cpp:1373`, `PixAllocaRegWrite::FromInst` takes `regBase` from the
referenced alloca node). Measured against that, the numbering is wrong by
exactly the six registers of the shadow range: `ValidateAllocaWrite(0)` wants 0
and gets 6.

The `expected.md` "does not reproduce" criterion — "the subroutine version
numbers the six members exactly as the non-subroutine version does" — is
unambiguously **not** met, and that is the criterion that decides `repros` here.
`match.json`'s predicate was written to the absolute quantity, and given three
controls in the correct direction.

## 4. History

`triage.py bisect` cannot drive this repro (it is not a `dxc` invocation), so
the release scan was hand-run by `history-2923.py` and captured in
`manual-case-history.txt`: for each release, that release's `dxc.exe` compiles
the shader and that release's `dxcompiler.dll` supplies the PIX passes
(`dxopt -external <dll> -external-fn DxcCreateInstance`). 22 builds, both
optimisation levels, repro and control:

| release | repro -Od | repro -O1 | control -Od | control -O1 |
| --- | --- | --- | --- | --- |
| v1.4.1907 | invalid-probe | invalid-probe | invalid-probe | invalid-probe |
| v1.5.2003 | no-match | no-match | no-match | no-match |
| v1.5.2010 | no-match | no-match | no-match | no-match |
| v1.6.2104 | no-match | no-match | no-match | no-match |
| **v1.6.2106** | **match** | **match** | no-match | no-match |
| v1.6.2112 … v1.9.2607 | match | match | no-match | no-match |
| main-debug ab5400907 | match | match | no-match | no-match |

* v1.4.1907 predates `as_6_5` and never ran the repro — an invalid probe, the
  same trap already recorded on #3251 and #3259.
* The control never matches at any release, so the predicate is not simply
  firing on everything old.
* **Transition: v1.6.2104 (2021-04-20) → v1.6.2106 (2021-07-01).** The IR shape
  is identical on both sides — the same seven annotated allocas, the same six
  `DW_OP_bit_piece` shadows for `main`'s `p` (`DW_TAG_auto_variable`, line 19).
  What changes is that at v1.6.2104 each of those six carries a write:

  ```
    %1     [1 x float]   regs[0] base=0 count=1
           declares: p [DW_TAG_auto_variable src-line 19] !DIExpression()
           writes  -> registers: 0
  ```

  and from v1.6.2106 onwards it reads `writes -> registers: (none)`. So this is
  not a renumbering; the writes that described the caller's variable stopped
  being emitted, leaving it mapped to registers nothing writes.
* The bands are clean — three consecutive `no-match` releases then eighteen
  consecutive `match` releases, at both optimisation levels, with the control
  flat across all of them. A nondeterministic symptom would speckle; this does
  not, so `--repeat` was not warranted.
* `manual-case-crossprobe.txt` runs the 2x2 of {dxc 2104, dxc 2106} x
  {passes 2104, passes 2106}. The result tracks the **pass** DLL, not the
  compiler: `dxc=2104/passes=2106` matches, `dxc=2106/passes=2104` does not. So
  what changed is in `lib/DxilPIXPasses`, not in the debug info `dxc` emits.
  Commits touching `lib/DxilPIXPasses` in that window (`git log`, not bisected —
  this is a list of candidates, not a finding): `320d40bf3` (#3746, "Change
  insertion point to after referenced value"), `ba1900c9d` (#3756),
  `e46fa6b4f` (#3786, "Find correct type of struct members, add instructions
  only after phi nodes"), `ad4a3ea92` (#3805), `ec7e33230` (#3819),
  `650de80d3` (#3855, "Don't seek beyond terminator instructions
  (value-to-declare pass)").

  *Corrected at collation:* the commit actually inside the window is
  `dad1cfc30` (#3855)(#3856), the release-branch cherry-pick of `650de80d3` —
  same change, different SHA; `650de80d3` itself is not an ancestor of
  v1.6.2106. Re-derived by `window-commits.py` into
  `manual-case-window-commits.txt`: the window holds **nine** commits touching
  `lib/DxilPIXPasses/` (the six above plus `cb485263b` #3654, `ea1efe96b`
  #3628, `880c1359c` #3594), **five** of which touch
  `DxilDbgValueToDbgDeclare.cpp` and **one** `DxilAnnotateWithVirtualRegister.cpp`.
  Still candidates, not a finding.

### The honest caveat about the report itself

**This repro does not reproduce at the vintage of the report.** The issue was
filed 2020-05-27; the release current at that moment is v1.5.2003 (2020-03-25),
and there `repro.hlsl` is numbered perfectly — registers 0..5, all written, one
per member. The signature measured here first appears fourteen months later.

The issue itself says *"Not clear yet what set of structs are affected"*, so the
reporter's actual shader is not recoverable from the text; `repro.hlsl` is a
guess at it, built from the literal edit the issue describes. The conclusion
that stands is: **the scenario the issue describes does produce wrong PIX member
numbering on current `main`**. Whether it is the same instance @jeffnn hit in
2020 cannot be established from what the issue says.

Note also that the PixTest emulation column in `manual-case-history.txt` is
noisy before v1.7.2207: the *control* also reads `test-FAILS` on older releases,
because those compilers produced a different debug-info shape at `-Od` than
today's test expects. That is exactly why "the unit test fails" was rejected as
the predicate in favour of the numbering check.

## 5. Labels

Currently none. Proposed (recorded, not applied):

* `PIX` — "Issues related to PIX passes". Exact fit; the defect is in
  `lib/DxilPIXPasses`.
* `bug` — "Bug, regression, crash". It is a bug, and the release scan shows a
  regression point.
* `debug info` — "Related to debug info generation". The wrong metadata is
  derived from `llvm.dbg.value`/`llvm.dbg.declare` by
  `DxilDbgValueToDbgDeclare`.

Deliberately not proposed: `correctness` ("Bugs that impact shader
correctness") — the generated shader is correct, only the PIX debug metadata is
wrong; `validation` — that means DXIL validation specifically, and `dxv` is not
involved; `incorrect-code` — that is about handling *invalid input*;
`check-in-clang` — the PIX passes have no clang counterpart; `crash` — nothing
crashes.

## 6. Compiler Explorer

Skipped, with the reason recorded in `verdict.json`. CE runs `dxc` only; the
symptom is in metadata added by `dxopt`-driven PIX passes that CE cannot run,
and `repro.hlsl` compiles cleanly (exit 0, no diagnostics) on every release
tested — a link would show a clean compile and nothing about the defect.

## 7. Suggested action

`still-valid-keep-open`, and it is now cheap to answer @damyanp's 2024 question:
yes, the scenario still misbehaves, here is a command-line repro that does not
need a modified unit test. Confidence `high` that the numbering is wrong on
`main`; the caveat in §4 is about provenance, not about the measurement.

## 8. Artifacts

| file | what |
| --- | --- |
| `repro.hlsl` | the payload struct passed by value to a subroutine that calls `DispatchMesh` |
| `control-no-subroutine.hlsl` | `PixStructAnnotation_SequentialFloatN`'s shader verbatim |
| `control-inout-param.hlsl` | `repro.hlsl` with `inout` — isolates the by-value copy |
| `run-2923.cmd` | the four-tool pipeline; `PIX_DXC`/`PIX_DLL`/`DXC_BIN` overridable |
| `check-2923.py` | reads the annotated IR, reports the numbering, emits the predicate marker |
| `history-2923.py` → `manual-case-history.txt` | the 22-build release matrix |
| `crossprobe-2923.py` → `manual-case-crossprobe.txt` | dxc-vs-pass-DLL 2x2 across the transition |
| `out-main-debug-pix.txt` | the primary probe |
| `variant-*.txt` | five controls/variants, all with declared `# expect:` |
| `*-Od.annotated.ll`, `*-O1.annotated.ll` | the annotated IR from **main-debug** (see `method-notes.md`: re-running `history-2923.py` overwrites these) |
