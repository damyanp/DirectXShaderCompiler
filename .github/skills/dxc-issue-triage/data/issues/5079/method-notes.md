# Method notes -- #5079

Observations worth considering for promotion into `SKILL.md` at collation. Not
applied here; recorded per the per-issue convention.

## A same-shaped control needs the same minimal shape as its positive case

Building `control-directx-headers-only.cpp` around `<directx/d3d12shader.h>` (to
mirror the reporter's own include list more literally) produced `unknown type
name 'THIS'` / incomplete-type / `'virtual' can only appear on non-static member
functions` errors from that header's COM interface declarations -- neither
shim's non-Windows path defines the bare `THIS` COM-IDL macro (only `THIS_`).
This is real, but it is a *different, pre-existing* gap in this exact
combination of vendored headers, unrelated to the typedef-redefinition conflict
under test -- and because `-ferror-limit` kicked in, it fully masked whether
the actual conflict was even reached, in both the control and (transiently)
the main repro.

The fix was to drop `d3d12shader.h`/`<unknwn.h>` from both the repro and the
control and reference the conflicting type names directly (`BYTE`, `BOOLEAN`,
`BOOL`, `LONG`, `ULONG`, ..., `GUID`, `REFGUID`) -- which is *closer* to the
reported symptom, not weaker: the reporter's own error transcript never
mentions a COM-interface error either, every line they quote is a typedef/
`_GUID` redefinition. The general lesson: when a control fails for a reason
that doesn't match the issue's own reported symptom, that is a signal the
control (or the repro) is exercising more machinery than the issue actually
needs, not a signal to add scaffolding to route around it. Minimize to the
narrowest thing that reproduces the *exact* reported diagnostic class first;
only add back the extra headers if the narrower version fails to reproduce
anything.

## Generator scripts that shell out and capture output must redact paths themselves

`gen-manual-case.py` computes absolute include paths (`-I<repo>/...`,
`-I<issue>/posix-shim`, `-include<issue>/posix-locale-prelude.h`) and a clang
subprocess necessarily echoes them back verbatim in both `-Wmacro-redefined`
"previous definition is here" notes and in every diagnostic's file:line
prefix. The first draft of this generator wrote `subprocess.list2cmdline`
output and `proc.stdout`/`proc.stderr` straight to the `manual-case-*.txt`
captures with no redaction step, which `scripts/check_paths.py` (run as a
read-only sanity check, not a required step of the per-issue workflow) caught
as 96 leaked this-machine checkout-root occurrences across the three
captures (the drive-letter-plus-checkout-directory prefix `check_paths.py`'s
`MACHINE_PATH` pattern exists to catch).

The skill's shared `redact_paths()` (in `triage.py`, used internally by
`run`/`bisect`) is exactly the tool for this and is safe to *import* (never
edit) from an issue-local script: it tokenises `<repo>`/`<triage>`/`<cache>`
prefixes by the same rule `triage.py` itself uses for `.hlsl`-driven captures,
so a manual, non-`dxc.exe` capture ends up byte-for-byte consistent with the
convention the rest of the workflow already enforces, instead of an
issue-local re-implementation that could drift from it. General lesson: any
issue-local script that shells out to a *non-dxc* compiler and captures raw
stdout/stderr needs the same path-redaction discipline `triage.py` already
applies to `cmd.txt`/`run` captures -- it is easy to forget precisely because
`check_paths.py` is not in the per-issue step list, and the leak is invisible
until something greps for it.

## Dating a submodule's own history matters as much as dating a file's

`git log --all --reverse -- external/DirectX-Headers` (not just `git log`,
which returns commits in graph-traversal order, not date order, for a path
touched by both mainline and merge commits) was needed to establish that the
single commit that *added* the DirectX-Headers submodule (`14a55b773`,
2022-11-23) is also the *only* commit that has ever touched its pin --
i.e. the pin has been static since day one, not merely "hasn't changed
recently". This is the same class of trap `SKILL.md` already documents for
dating a symbol's introduction (`git log --all -S` vs. a current-path-scoped
search), applied one level up: to a vendored dependency's pin history, not a
symbol inside a single file.
