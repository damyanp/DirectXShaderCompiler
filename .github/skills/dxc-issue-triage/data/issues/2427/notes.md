# #2427 Compiler fails on quoted folder parameters finishing with '\\'

**Verdict: still reproduces - but reproducing it is not the finding.** The failure is
correct platform behaviour, already diagnosed in-thread in 2019. The finding is that the
**agreed fix has lapsed**.

## The failing command still fails

Run through `cmd.exe` verbatim (PowerShell re-quotes arguments and would have masked this):

| # | command | exit | result |
| --- | --- | --- | --- |
| A | `-Fd "dbgdir\" mySimplePS.hlsl` | 1 | `dxc failed : Required input file argument is missing.` |
| B | `-Fd "dbgdir"\ mySimplePS.hlsl` | 0 | works (@pow2clk's transposition) |
| C | `-Fd dbgdir\ mySimplePS.hlsl` | 0 | works (unquoted) |
| D | `-Fd "dbgdir\\" mySimplePS.hlsl` | 0 | works (doubled backslash) |

Case A is the reporter's exact command line and still fails identically, seven years on.
On success a `.pdb` is auto-named into the directory, so `-Fd`'s directory mode itself works
whenever the argument survives the shell.

## Why "still reproduces" is the uninteresting half

@pow2clk established in 2019 that the trailing backslash escapes the closing quote during
**argv splitting**, before dxc sees anything; the process receives 6 already-merged
arguments. FXC behaves the same way. This is documented C runtime / shell behaviour, so it
must reproduce, and "confirmed still broken" would be a misleading summary.

## What actually changed since the thread went quiet

The agreed resolution was a new flag taking a directory without a trailing separator.

- `-Fdd` / `-Fad` / any `DebugDir` option: **does not exist** in current `dxc --help` or in
  `include/dxc/Support/HLSLOptions.td`.
- **PR #2430** ("Add Fdd option") - closed unmerged, 2020-01-23.
- **PR #2660** ("Fad option for automatic debug output", @pow2clk, `Fixes #2427`) - open
  from 2020-01-23 until **closed unmerged on 2026-01-22** by an inactivity sweep:
  "This PR was closed as it has not been updated in the last two years."

@damyanp's June 2024 comment - "there may be a PR that addresses this still open and we'll
accept that if someone wants to rebase it and finish it off" - was accurate then, but the
PR it refers to has since been swept closed. The issue currently has **no** path to
resolution.

## Assessment

Keep open as an enhancement, and note that reviving PR #2660 is the concrete next step. The
issue is also **unlabelled**, which is likely why it fell through.
