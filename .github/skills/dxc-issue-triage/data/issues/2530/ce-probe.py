"""Probe one Compiler Explorer compiler with one local shader, and print the
result verbatim.

Exists because #2530's evidence includes two *cross-compiler* claims -- that FXC
accepts the repro and that clang's HLSL front end rejects it -- and neither is a
`dxc` invocation, so `triage.py run` cannot capture them. SKILL.md's rule is that
a claim published in a comment must be re-runnable by a stranger from the repo,
so the probe lives next to the evidence rather than in a shell history.

It reuses triage.py's `ce_compile`, so a pane probed here is compiled exactly the
way `triage.py godbolt` compiles it -- same filters, same API call. Nothing here
publishes or shortens a link.

    python ce-probe.py <compiler-id> <shader.hlsl> <args...>

e.g.
    python ce-probe.py fxc_10_0_19041 repro.hlsl /T ps_5_0 /E main
    python ce-probe.py hlsl_clang_trunk repro.hlsl -T ps_6_0 -E main -fsyntax-only
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "scripts"))
import triage                                             # noqa: E402


def main():
    compiler, shader, args = sys.argv[1], sys.argv[2], " ".join(sys.argv[3:])
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, shader), encoding="utf-8") as f:
        source = f.read()
    rc, text, crashed = triage.ce_compile(source, compiler, args)
    print(f"$ [compiler-explorer] {compiler} {args}  ({shader})")
    print(f"[exit] {rc}{'  CRASH' if crashed else ''}")
    print("--- output ---")
    print(text)


if __name__ == "__main__":
    main()
