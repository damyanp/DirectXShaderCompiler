# Method notes from #4540

Four things this issue taught about the method. The first is the one worth promoting.

---

## 1. A control whose expected value equals the default result is not a control

This is the brief's "a predicate with no control is worthless" warning, met somewhere new —
not in the *predicate*, but in an *instrument*.

To find which pass narrows the groupshared global to `i1`, the obvious lever is
`dxc -Oconfig=<pass list>`. I built a leave-one-out sweep over the 116-pass pipeline, with what
looked like a proper control: replay the **full** pass list and check the result still matches
the default compile. It did. The sweep then reported that removing *any single pass*, including
`-globalopt`, changed nothing — i.e. no pass was responsible, which is impossible.

**`-Oconfig=` is a SPIR-V-only option.** It is declared in `spirv_Group` in
`include/dxc/Support/HLSLOptions.td:443` and is **silently ignored on a DXIL compile** — no
warning, no error, exit 0. Proof: an *empty* `-Oconfig` pass list still produces fully lowered
DXIL identical to the default. Every measurement in that sweep was void.

The control could not possibly have caught this, because **its expected value was the same as
the null result**. "Full pipeline behaves like the default" is true both when the option works
and when the option is ignored. A control only controls when passing it and failing it lead to
different worlds.

The replacement (`dxopt`) works precisely because its null control *differs* from its test:

```
front-end module, no passes      -> i32
dxopt with no passes  (control)  -> i32
dxopt -globalopt                 -> i1
full pipeline minus -globalopt   -> i32
```

**Rule of thumb worth carrying:** before trusting an instrument, ask what its control would
print if the instrument were doing *nothing at all*. If that is the value you expect to see
when it works, you have not built a control — you have built a formality.

`make-pass-attribution.py` keeps section 1 of its output devoted to the dead end, so the
artifact tells the next reader why `-Oconfig` is absent rather than leaving them to rediscover
it.

## 2. `!llvm.ident` beats `--version` as a per-release self-test

`SKILL.md` asks for a per-release self-test line in the same capture the predicate scores.
The natural way to write it is to shell out to `dxc --version` — but **releases older than
about v1.6 reject the flag** (`dxc failed : Unknown argument: '--version'`), which turns the
self-test into noise on exactly the oldest builds, where drift is most likely.

`!llvm.ident`, extracted from the emitted module, is strictly better:

- it is present on every release back to v1.4.1907;
- it is read from **the very module the predicate scores**, not from a separate process
  invocation, so it cannot be satisfied by a build that answered a different question;
- it gave 17 distinct strings across 22 builds, which is the actual evidence that distinct
  binaries answered — and it caught that v1.5.2003 through v1.7.2207 all report
  `clang version 3.7 (tags/RELEASE_370/final)`, i.e. `!llvm.ident` alone does **not**  distinguish those six builds. Worth knowing before leaning on it as an identity check.

## 3. A CE source transformation needs the control run on the *known-good* arm too

CE gives every pane one shared source, so an A/B has to be folded behind `#ifdef`. `SKILL.md`
already says a transformed repro is a different program until shown otherwise. The specific
trap: it is natural to check only that the folded file still *reproduces*.

That check passes even if the guard is broken in a way that disables the construct in the
control arm — which would make the CE link show a spurious contrast. `make-godbolt-transform-case.py`
therefore compiles the folded file **both** ways against **both** untransformed originals, under
CE's own argument set (`-Zi -Qembed_debug`, which CE appends and which can change what is
emitted), and requires 2/2 agreement.

Related and cheap: CE compiles the annotation banner into `!dx.source.contents`, so a banner
that names the literal token the reader is told to look for (`i1`) puts that token in every
pane's output including the correct one. Write the banner in words — "a 1-bit integer type" —
not in tokens.

## 4. Small tooling frictions

- **`triage.py` Python API**, for generators that need the release list: `triage.con()` (a
  `sqlite3` connection with `sqlite3.Row`), `triage.resolve_compiler(name)` → a **path string**,
  `triage.redact_paths(text)`. There is no `triage.db()` and no `triage.load_compiler()`; I
  wrote both from a plausible guess and had to fix them. The `runs` table's issue column is
  `issue_number`, not `issue`.
- **`dxopt` from PowerShell** needs `-o=` and the input path quoted —
  `dxopt.exe "-o=out.bc" "in.bc" -opt-mod-passes <passes...>` — or it fails with `0x80070002`,
  which reads as "file not found" and sends you looking in the wrong place. Disassemble the
  result with `dxc -dumpbin out.bc`; `dxa -listparts` returns `0x80070057` on a raw module.
  `dxc -Odump` prints the default pipeline; keep the lines starting with `-`.
- **`audit` counts `.hlsl` files, not just the ones you meant to probe.** Adding
  `godbolt-source.hlsl` for publication made `audit` fail with "has no captured output" until it
  was run through `run --shader … --label …`. That is the right behaviour — an unprobed shader
  in an issue directory is exactly the kind of thing that rots — but it is worth knowing that
  publishing to CE creates an audit obligation.
- **The agent `grep` tool silently returns zero matches for files under `.github/`.** Not "no
  such file", not an error — an empty result, which is indistinguishable from a genuine miss and
  will quietly convince you a string is absent. `Select-String` works. This cost real time; a
  line in `SKILL.md`'s setup section would save the next worker the same.
