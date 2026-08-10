# Method observations from #4350

Collation should decide what, if anything, is worth promoting. Nothing here has been applied
to `SKILL.md` or `triage.py`.

## 1. Redaction hid a broken path in a generator script, and the artifact looked fine

`capture-stack.py` computed the repository root five levels up from
`data/issues/4350/` when it is six. The resulting `dxc.exe` path did not exist, `cdb` reported
`Win32 error 0n2`, no frames were captured — and because `redact()` rewrote the machine root
to `<repo>` before writing, the committed capture displayed a **plausible, correct-looking**
`<repo>\build\Debug\bin\dxc.exe` in its `$` line. The only visible symptom was
`(no C++ exception frames captured)`, which reads as "the debugger found nothing", i.e. as a
result rather than as a failure.

This is the `SKILL.md` rule "a negative result from a command that errored is not a negative
result", but with the redaction step actively concealing the errored input. Redaction and
path-validity checking interact: the same substitution that makes an artifact machine-independent
also makes a wrong path indistinguishable from a right one.

The fix that worked, and that might generalise to any generator writing a `manual-case-*.txt`:
**assert every path exists before running, and fail loudly rather than emitting a capture.**
`capture-stack.py` now exits 2 with the unredacted path on stderr if `dxc.exe` is not where it
computed. Two lines, and it converts a silent false negative into a stop.

Possible tooling change for collation to weigh: `check_paths.py` verifies that no *machine*
path is committed; nothing verifies that a `<repo>`-relative path in a committed artifact
still resolves. A checker that expands `<repo>` and stats the result would have caught this.

## 2. `cdb` needs three separate quoting decisions to survive Python -> cmd.exe

`SKILL.md` says run `cdb` through `cmd.exe`, not PowerShell. Going through Python's
`subprocess` to `cmd.exe` needs more than that, and each failure looked like a different bug:

- passing a list and letting `list2cmdline` quote it re-quotes the embedded `\"` in the `-c`
  script, so `cdb` never sees its command;
- passing `cmd.exe /c "<command>"` where `<command>` itself starts with a quoted program path
  gives `'"C:\Program Files…\cdb.exe"' is not recognized`, because `cmd /c` strips the outer
  quote pair. The whole command needs one *extra* enclosing pair;
- quoting the **debuggee** path (`"…\dxc.exe"`) makes `cdb` treat the quotes as part of the
  filename: `Cannot execute '"…\dxc.exe" -T vs_6_0 repro.hlsl', Win32 error 0n2`. The
  debugger path may be quoted; the target's must not be.

The combination that works, as a single string passed verbatim to `subprocess.run`:

```
%ComSpec% /c ""<cdb path>" -c "sxe -c \"kn 25; gh\" e06d7363; g; q" <dxc path> <args>"
```

Note the third bullet produces the *same* `Win32 error 0n2` as observation 1, from a completely
different cause. Two distinct defects with one error message, inside one script.

## 3. This issue is an unusually clean specimen of the multi-signature hazard

`manual-case-predicate-counterfactual.txt` measures five predicates over the 20 committed
release captures. Because **every** release reproduces, every wrong predicate manufactures a
boundary out of nothing rather than merely shifting one:

- exit-status-only: "fixed at v1.7.2207" — 15 of 20 releases wrong, and wrong about today;
- the reporter's own quoted message: "regressed at v1.6.2106";
- the phrase from the issue *title*: a fix window that does not exist.

Worth noting for the skill's exit-code table: `DXC_E_LLVM_CAST_ERROR` appears here as **both**
`0x80AA001D` (v1.6.2106, v1.6.2112) and `0x80004005` (v1.7.2207 onward) for the identical
defect and the identical message. The table records both rows separately; this issue shows the
transition between them happening under one bug, so neither row is a property of the failure.

Something the counterfactual pattern gained here that `#3954`'s did not have: **scoring the
controls under the same predicates.** `nonzero exit` gets this issue's history exactly right —
20 of 20, same as the predicate actually used — and is still the wrong predicate, which is only
visible because `control-syntax-error.hlsl` exits `0x80004005`, the same status as the repro,
and `nonzero exit` fires on it. A counterfactual that only scores the repro cannot distinguish
"right" from "accidentally right". Suggest the reusable shape is: score every predicate against
both the probes and the controls, in one table.

## 4. `--compilers` accepts the same compiler id twice, which is how a control pane is built

`ce_compiler_specs` builds a list, not a dict, so
`hlsl_clang_trunk:<args>,hlsl_clang_trunk:<args> -DCONTROL` yields two panes of the same
compiler differing in one define, and the shortlink read-back confirmed all four panes stored.
`SKILL.md` documents the `-D<CONTROL>` guard trick but pairs it with "add a second pane"
without saying the second pane may be the *same* compiler; using a different build (the
assertions variant) to get a second pane would confound build and flag. Might be worth one
clause.

## 5. A cross-issue note, deliberately kept out of the draft

The issue body opens "Related to #4340." #4340 is closed, and reaches the const-ness of the
implicit object through a different surface: an overloaded `operator[]` on a struct reached
through `ConstantBuffer<>`. Notably it is *diagnosed* — "'this' argument has type
'const BindlessTexture2D', but method is not marked const" — where #4350 is an internal error,
so if they are one defect the difference is which paths reach a diagnostic before lowering.
It is labelled `hlsl2021` where this is `hlsl-next`. Whether they are the same defect is a
collation judgement and the draft says nothing about it.
