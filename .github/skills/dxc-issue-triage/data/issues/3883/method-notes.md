# Method observations from #3883

For collation to promote or discard. Nothing here was written into `SKILL.md` or
`scripts/triage.py`.

## 1. This issue is a ready-made worked example for the `internal_failure` rule, in both directions

SKILL.md already says a crash predicate must be exit-status-based, and gives #3259 (an
internal failure that prints nothing) and #8737 (a cast error that exits E_FAIL) as separate
examples. **#3883 contains both across all 20 stable releases**, with the separately measured
v1.5.2003 prerelease retained as supplemental evidence and no fix anywhere in the captures:

| releases | exit | stderr |
| --- | --- | --- |
| v1.4.1907, v1.5.2003, v1.5.2010 | `0xC0000005` | completely empty |
| v1.6.2104 | `0xC0000005` | `Internal compiler error: access violation…` |
| v1.6.2106, v1.6.2112 | `0x80AA001D` (`DXC_E_LLVM_CAST_ERROR`) | `Internal Compiler error: llvm::cast<X>()…` |
| v1.7.2207 … v1.9.2607 | `0x80004005` (E_FAIL) | `error: llvm::cast<X>()…` |
| `main` Debug | `0xE0000001` | `Internal compiler error: LLVM Assert` |

- a **text** predicate invents a regression at v1.6.2104 (the three oldest print nothing);
- a **status-code-only** predicate invents a fix at v1.7.2207 (E_FAIL is indistinguishable
  from an ordinary error by status alone);
- a **nonzero-exit** predicate would score the *fix this issue asks for* — a proper `error:` —
  as the bug.

Only `is_internal_failure()`'s combination of status codes **and** the `cast<X>()` text marker
gets all 22 captures right. If a single citation is ever wanted for that rule, this is a
better one than any of the three currently used, because one issue exercises every arm.

The committed `signature-census.py` reduces the captures to that table in one command; it is
generic apart from the header text and might be worth generalising into
`triage.py` (e.g. `triage.py sql`-driven, or a `--census` flag on `bisect`).

## 2. `0x80AA001D` is worth adding to SKILL.md's measured exit-code table

The table lists 0xC0000005, 0xC00000FD, 0x80000003, 0xE0000001-3 and E_FAIL, but not the
`FACILITY_DXC` HRESULTs. v1.6.2106 and v1.6.2112 return `DXC_E_LLVM_CAST_ERROR`
(`0x80AA001D`, `include/dxc/Support/ErrorCodes.h:149`) for the *same* failure that later
releases flatten to E_FAIL. It was scored correctly here — but by the text marker, not by the
status — so a hypothetical release that returned `0x80AA001D` silently would be missed.
`0x80AA001C` (`DXC_E_LLVM_UNREACHABLE`) is the neighbouring case.

## 3. Compiler Explorer reports the low byte of the Windows HRESULT as the exit code

`dxc_1_6_2112` shows `exit=29`, `dxc_trunk` shows `exit=5`. Those are `0x80AA001D & 0xFF` and
`0x80004005 & 0xFF` — the Linux `exit()` truncation of the same HRESULTs measured locally.
Useful for reading a CE pane against a local run, and a reason not to compare CE exit codes to
Windows ones numerically. (SKILL.md notes 139/134 for signals but not the truncation.)

## 4. `godbolt --skip`-vs-publish: an FXC pane changed the value of the link completely

The default two-DXC link showed two panes failing with an internal error — true, but it does
not show what *should* have happened. Probing `fxc_10_0_19041` first (through a local
`ce-probe.py`, because `godbolt` prints only the first line) found
`error X4000: variable 'index' used without having been completely initialized`, which turns
the link into a side-by-side answer to the reporter's actual ask and justified the
`fxc-disagrees` label. This matches SKILL.md's #1627 lesson ("revisit that call once you have
tried a Clang pane") but for FXC, and the general form seems to be: **for any "the compiler
should have diagnosed this" issue, probe FXC before deciding what the link is for.**

## 5. `triage.py fetch` does not record the issue author's login

`issue.json` carries `author.login` for each **comment** but no author for the issue itself,
while SKILL.md's rule is "verify every handle against `issue.json`'s `author.login`". Here the
issue author (`Tom-Lopes`) had to come from a separate `gh issue view --json author`. Either
`fetch` should add `author` to its `--json` list, or the rule should say where to look.

## 6. A `.cmd` harness must be invoked as `.\name.cmd` from `cmd /c`

`cmd /c 'assert-stack.cmd > raw.txt'` from the agent's PowerShell tool answers
`'assert-stack.cmd' is not recognized…` — the current directory is not on `PATH` under this
invocation. It produced a 2-line "output" file that looked like a failed capture rather than a
failed launch, which is SKILL.md's "a negative result from a command that errored" one level
down. `.\assert-stack.cmd` works. Worth a sentence next to the existing "run `cdb` through
`cmd.exe`, not PowerShell" note.

## 7. `sxe -c "kb N; gh" e0000001` printed more frames than `N`

`kb 9` yielded 9 named frames but `kb 14` yielded ~20, so the count is not a reliable cap when
several asserts fire in sequence. Not worth tooling; just check the transcript length before
committing it, and re-run with a smaller `N` rather than post-trimming the frames, so the
committed capture is exactly what the debugger produced.

## 8. Deliberate non-use of `--repeat`

The symptom is fully deterministic in *occurrence* (22/22 captures) even though its *form*
varies across builds. Per SKILL.md's #3377 note that is the case `--repeat` does not protect —
there is no clean result anywhere in the scan that could have been an unlucky probe — so it
was not used, and the varying form was measured as a per-release census instead.

## 9. `gh` past the assert also names the release-build failure site — and refuted a source reading

SKILL.md sells `gh` (NDEBUG emulation) as a way to see the *symptom* a Release build would
show. It is also the cheapest way to see **where** that symptom comes from, and here that
mattered: reading `Constant::getUniqueInteger()` says the release path ends at
`cast<ConstantInt>(C)` on `Constants.cpp:1449`, and that is wrong. Breaking on the C++
exception instead —

```
cdb -c "sxe -c \"gh\" e0000001; sxe -c \"kb 6\" e06d7363; g; q" <dxc.exe> <args...>
```

— puts the failure in `cast<StructType>` inside `Type::getStructNumElements`, reached via
`UndefValue::getNumElements`, one call further out. Nothing in the twenty-one release captures
could have told the two apart: both print the identical
`cast<X>() argument of incompatible type!`.

The generalisable form: **`sxe -c "gh"` on the assert code plus `sxe -c "kb N"` on
`e06d7363` names the throw site of any `hlsl::Exception`**, which is what DXC's surviving
`cast` checks raise in Release. Worth adding beside the two existing incantations, because a
source-read attribution of a cast failure is exactly the kind of claim that looks verified and
is not.
