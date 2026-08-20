# Method notes — #4858

**An unbounded "does X appear after Y" regex over a full DXIL disassembly will match the
trailing `declare` line, not just a real occurrence in the block you meant.** Every DXIL
disassembly ends with a `declare <ret> @dx.op.<name>...` line for every intrinsic the module
calls, regardless of where the call sites are. A first draft of this issue's predicate was

```
br i1 [^\n]*, label %(\d+), label %\d+\r?\n\r?\n; <label>:\1\b[\s\S]*?dx\.op\.calculateLOD
```

intending "the literal text `dx.op.calculateLOD` appears somewhere in the named successor
block." Tested against the `-Od` control (which does *not* sink the call — it stays in the
unconditional entry block, before the branch), this matched anyway, because the non-greedy
`[\s\S]*?` simply kept scanning past the successor block's end, past the next label, past the
closing `}`, until it hit the module's trailing `declare float @dx.op.calculateLOD.f32(...)`
line — present in *every* capture that calls the intrinsic at all, sunk or not. The predicate
scored a known-clean control as a reproduction, and would have scored `no-repro` releases as
`repro` identically.

The fix was to bound the scan with a negative lookahead so it cannot cross into the next block
or out of the function:

```
br i1 [^\n]*, label %(\d+), label %\d+\r?\n\r?\n; <label>:\1\b(?:(?!\n; <label>:|\n\})[\s\S])*?call[^\n]*@dx\.op\.calculateLOD
```

and requiring `call` immediately before the op name, so a bare textual mention (as in a
`declare` or a comment) cannot satisfy it. Verified against both the repro (match) and the
`-Od` control (no-match) before being adopted; see `match.json`'s `note` and
`variant-control-od-main-debug.txt`.

This generalises the already-documented "a control cannot catch a broken reader" trap (#2923) one
step further: here the reader (regex) was not merely imprecise, it was *unbounded* — a predicate
that says "X appears somewhere after Y" over disassembly text should default to suspicion,
because DXIL's trailing `declare` block guarantees a same-named late occurrence of almost any
opcode string the module uses at all. Bound the scan to the enclosing block/function before
trusting a naive "appears after" pattern over full module disassembly, not just over a single
instruction line.

**`-Zi -Qembed_debug` (Compiler Explorer's default DXC pane flags) renames anonymous basic
blocks from numeric labels (`%9`) to source-derived ones (`if.then`/`if.end`).** A predicate
anchored on `label %(\d+)` — reasonable for the tool's own default (no `-Zi`) capture — silently
does not fire on a `-Zi` capture of the same defect, and doing so is a predicate-portability gap,
not a fixed result. Confirmed by direct inspection (`gen-zi-sinking.py` /
`manual-case-zi-sinking.txt`): the same sinking is present under `-Zi`, in an `if.then:` block
instead of a numbered one. This capture is read manually rather than scored through
`match.json`, and that limitation is stated in `notes.md` rather than left implicit. A future
predicate wanting to cover both label styles would need `label %(\w+)` and the corresponding
`; <label>:\1\b` / `\1:\s*\n` forms for both spellings.
