"""Record the #4614 verdict.

Driven from Python rather than the shell so PowerShell cannot mangle the
prose: SKILL.md records that a double-quoted PowerShell string silently eats
`$` (variable expansion) and turns a backtick escape into U+001B, and both
have reached committed artifacts before. subprocess with an argv list has no
such layer.

Re-runnable: `verdict` upserts, so running this again restores exactly these
fields.

Run from this directory:  python record-verdict.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TRIAGE = os.path.join(SKILL, "scripts", "triage.py")

HISTORY = (
    "always-repro'd across all 20 stable releases v1.4.1907 (2019-07) .. "
    "v1.9.2607 plus main-debug, established by a LINEAR scan; 1 release with "
    "no usable dxc asset (v1.2.0-alpha) and 5 probeable prereleases "
    "(v1.5.2003, v1.8.2306-preview, v1.8.2405-mesh-nodes-preview, "
    "v1.10.2605.2, v1.10.2605.24) were excluded by policy. No invalid probes: "
    "no build emitted a diagnostic. NO REGRESSION WINDOW EXISTS in any "
    "shipped release, so the title's 'regression' is not a bisectable claim "
    "about release binaries -- v1.6.2106, the first release containing "
    "527d58e5a (PR #3827, 'Fixes #3016'), hangs on this repro like every "
    "other release; that boundary was confirmed with git merge-base "
    "--is-ancestor run over all 20 scanned tags, three of which answer 'not "
    "contained', so the check discriminates. v1.4.1907 is the bisection "
    "floor, so 'always' means 'for as long as it is checkable', which still "
    "predates the 2020-07 filing of the predecessor issue by a year."
)

SUMMARY = (
    "ONE defect, TWO signatures, and the composed predicate is what makes it "
    "visible: all 20 stable release binaries HANG on the repro (timeout, no "
    "output) while assert-enabled main-debug fails internally in seconds "
    "(0xE0000001, assert(0 && \"Type mismatch.\") at "
    "ScalarReplAggregatesHLSL.cpp:2690 in SROA_Helper::RewriteBitCast, the "
    "same inner three frames #3016 reported). match.json is "
    "any_of[timeout, internal_failure]: a bare internal_failure predicate "
    "scores all 20 releases clean and a bare timeout predicate scores ground "
    "truth clean, so either alone reports this open bug as fixed. NOT an "
    "NDEBUG artefact -- continuing past the assert with cdb 'gh' lands "
    "immediately on DXC's own detector, \"Infinite loop while SROA'ing value, "
    "use isn't getting eliminated\" (:2996), and under NDEBUG that guard "
    "expands to do { (void)(local); } while (0) "
    "(include/dxc/Support/Global.h:362) while the :2690 assert falls through "
    "to a bare return, so release builds spin instead of stopping; v1.9.2607 "
    "ran 300s with no output and its stacks 60s apart are identical at a "
    "fixed depth. History: no shipped release ever compiled this shader. The "
    "commit that closed #3016 changed SROA_Parameter_HLSL::flattenArgument, "
    "not RewriteBitCast, and the test it added "
    "(HLSLFileCheck/hlsl/types/struct/embeddedEmptyStruct.hlsl -- no base "
    "class, no empty-struct assignment) still compiles clean today while this "
    "repro does not. Four controls all no-match, including that test's shader "
    "and a variant holding BaseStruct as a member instead of a base, which "
    "narrows the trigger to assigning to an empty member reached through an "
    "empty base. repro.hlsl is sha256-identical to "
    "the issue body and to the maintainer's 2024 Compiler Explorer link."
)

TEXT_STALE = (
    "Title says 'regression'; for the attached repro no release regressed -- "
    "all 20 stable releases v1.4.1907..v1.9.2607 fail, including v1.6.2106, "
    "the first containing 527d58e5a ('Fixes #3016'). The body itself hedges "
    "this ('Unknown if it is exact same issue or just similar'), and the "
    "reporter's own production shader, which he says he worked around locally "
    "and then met again elsewhere, is not what was measured."
)

ARGS = [
    sys.executable, TRIAGE, "verdict",
    "--issue", "4614",
    "--batch", "batch-016",
    "--title", "Assert/hang in SROA_HLSL pass related to empty base struct regression",
    "--url", "https://github.com/microsoft/DirectXShaderCompiler/issues/4614",
    "--created-at", "2022-08-24T06:50:09Z",
    "--labels", "crash",
    "--status", "repros",
    "--repro-quality", "complete",
    "--history", HISTORY,
    "--confidence", "high",
    "--suggested-action", "still-valid-keep-open",
    "--summary", SUMMARY,
    "--text-stale", TEXT_STALE,
    "--notes-path", "issues/4614/notes.md",
    "--triaged-with-commit", "13730886e",
    "--triaged-by", "claude-opus-4.7 (GitHub Copilot CLI)",
    "--godbolt-url", "https://godbolt.org/z/erb45rxTb",
    "--labels-now", "crash",
    "--labels-add", "type-system,test",
]

if __name__ == "__main__":
    print(subprocess.list2cmdline(ARGS[2:]))
    sys.exit(subprocess.run(ARGS).returncode)
