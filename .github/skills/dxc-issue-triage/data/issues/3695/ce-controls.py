"""#3695: Compiler Explorer controls, run beside the published link.

`triage.py godbolt` publishes repro.hlsl on three panes. This adds the controls
that link needs but cannot itself carry:

  * control-valid.hlsl on the Clang pane -- Clang's DXIL backend is incomplete,
    so a Clang error is not evidence until a known-good input compiles with the
    same flags (SKILL.md). This is that check. It FAILS at the default flags
    ("DXIL Store not implemented for texture resources"), so the control is
    repeated with -fsyntax-only, which asks the narrower question the front end
    can still answer. The repro is run the same way, to show its error comes
    from Sema and not from that backend gap.
  * minimal-crash.hlsl and minimal-assign.hlsl on the DXC and Clang panes, to
    confirm the local minimisation behaves the same on CE's Linux builds.

Requests use the same endpoint, language, filters and crash rule as
triage.py's ce_compile, imported from it rather than reimplemented, so a
result here is scored exactly as a pane result is.

Writes manual-case-ce-controls.txt.  Usage:  python ce-controls.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "..", "..", "scripts"))
sys.path.insert(0, SCRIPTS)

import triage  # noqa: E402  (path set above)

ARGS = "-T cs_6_0 -E main"
SYNTAX = ARGS + " -fsyntax-only"

CASES = [
    ("control-valid.hlsl", "hlsl_clang_trunk", ARGS,
     "CONTROL attempt 1: known-good input on the Clang pane at the repro's own "
     "flags. Expected to compile; it does NOT -- Clang's DXIL backend cannot "
     "lower a texture store yet. So this control cannot validate a Clang "
     "*backend* result, and the -fsyntax-only pair below is used instead."),
    ("control-valid.hlsl", "hlsl_clang_trunk", SYNTAX,
     "CONTROL attempt 2: same input, front end only. This is the control that "
     "counts: if it is clean, a Sema error on the repro is about the repro."),
    ("repro.hlsl", "hlsl_clang_trunk", SYNTAX,
     "The repro, front end only -- shows the Clang diagnostic comes from Sema "
     "and is not an artefact of the incomplete DXIL backend."),
    ("control-valid.hlsl", "dxc_trunk", ARGS,
     "CONTROL: known-good input on the DXC pane. Must compile."),
    ("minimal-crash.hlsl", "dxc_trunk", ARGS,
     "Does the local minimisation crash CE's Linux Release build too?"),
    ("minimal-crash.hlsl", "dxc_1_6_2112", ARGS,
     "Same, on CE's oldest DXC."),
    ("minimal-crash.hlsl", "hlsl_clang_trunk", ARGS,
     "Does Clang diagnose the minimised form?"),
    ("minimal-assign.hlsl", "dxc_trunk", ARGS,
     "Plain global-to-global assignment: diagnosed locally, not a crash."),
    ("minimal-assign.hlsl", "hlsl_clang_trunk", ARGS,
     "Same on Clang."),
]


def main():
    out = ["# #3695 Compiler Explorer controls, full pane output.",
           "# Written by ce-controls.py; rerun it to re-derive.",
           "# CE runs Linux RELEASE builds: a Debug-only assert cannot show",
           "# here, so a crash appears as SIGSEGV (exit 139).",
           "# ANSI SGR escapes below are what CE returned; they are not"
           " edited out.",
           ""]
    for shader, compiler, args, why in CASES:
        src = open(os.path.join(HERE, shader), encoding="utf-8").read()
        rc, text, crashed = triage.ce_compile(src, compiler, args)
        out.append("=" * 74)
        out.append("# shader:   %s" % shader)
        out.append("# compiler: %s" % compiler)
        out.append("# args:     %s" % args)
        out.append("# why:      %s" % why)
        out.append("# exit:     %s  %s" % (rc, "CRASH" if crashed else ""))
        out.append("")
        out.append(text)
        out.append("")
        print("%-20s %-17s %-28s exit=%-5s %s" %
              (shader, compiler, args, rc, "CRASH" if crashed else ""))

    path = os.path.join(HERE, "manual-case-ce-controls.txt")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print("wrote %s" % path)


if __name__ == "__main__":
    main()
