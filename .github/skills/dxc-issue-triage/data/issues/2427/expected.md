# Expected symptom - #2427 Compiler fails on quoted folder parameters finishing with '\\'

**Repro quality: complete, but this is NOT a shader-compilation issue.** The repro is a command
line; no HLSL construct is under test. Included in this batch deliberately, to check that the
workflow does not force a codegen-shaped verdict onto a driver/CLI issue.

## What was reported (2019-08-26)

```
dxc -T ps_6_0 /Zi -Fd "d:\debug_info_folder\" mySimplePS.hlsl
```
fails with `Required input file argument is missing. use -help to get more information.`

The trailing backslash escapes the closing quote, so `-Fd` swallows the rest of the line
including the input filename. `-Fd` *requires* a trailing separator to mean "directory, pick the
filename yourself", so the reporter cannot simply drop it.

## Established in the thread, and NOT in dispute

@pow2clk determined this is **the platform's argv splitting**, not DXC's parsing - the process
receives 6 arguments, already merged, before DXC sees anything. FXC behaves identically. So
"does this reproduce" is nearly uninteresting; it must, because it is how the C runtime and
POSIX shells both work.

## The real question this triage should answer

The issue's agreed resolution was a **new flag** taking a directory without a trailing
separator. Is that path still open? Specifically:

1. Does the failing command line still fail today? (expected: yes, and correctly so)
2. Does a directory-taking flag exist in current `dxc` under any spelling (`-Fdd`, `-Fad`, ...)?
3. What became of the PR @damyanp referred to in 2024 as possibly still open?

A verdict of `repros` here would be technically true and useless. The useful output is whether
the *fix* is still in flight.

## Caution

The test harness must not itself mangle the arguments. PowerShell re-quotes arguments before
handing them to a native process, so the failing command line must be issued through `cmd.exe`
exactly as a user would type it, and the argv DXC actually received must be shown.
