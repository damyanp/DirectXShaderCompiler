"""Generator for manual-case-lit-validator-coverage.txt (issue #5064).

Echoes every command before running it, per the skill's rule that a
manual-case capture must be regenerable rather than transcribed by hand.
This issue has no shader repro (it is a test-infrastructure request), so the
"instrument" being probed is the lit test-discovery tool and the git history
of the DXC source tree, not dxc.exe. Run from anywhere; git commands are
invoked against the DXC repo root via -C, and lit is invoked as a module
script against the build tree with build_mode=Release (the only build_mode
with a built llvm-config on this machine; --show-tests only discovers tests,
it does not execute dxc/dxv, so it does not require the Debug ground-truth
build and does not rebuild or relink any shared target).
"""
import subprocess
import sys
from pathlib import Path

# .../<repo>/.github/skills/dxc-issue-triage/data/issues/5064/<this file>.py
# -> parents[6] is <repo>.
REPO = Path(__file__).resolve().parents[6]
OUT = Path(__file__).parent / "manual-case-lit-validator-coverage.txt"
REPO_TOKEN = "<repo>"


def sanitize(text):
    """Scrub the absolute machine path out of any command/output text.

    Commands below are invoked with relative paths and cwd=REPO, but tools
    like lit can still echo an absolute path back in warnings/errors (it
    normalises the input path internally) -- scrub both slash styles and
    escaped-backslash (as seen in Python repr'd strings) forms defensively,
    per the path-hygiene rule that no machine-specific path may appear in a
    committed artifact.
    """
    repo_str = str(REPO)
    variants = {repo_str, repo_str.replace("\\", "/"), repo_str.replace("\\", "\\\\")}
    for variant in variants:
        text = text.replace(variant, REPO_TOKEN)
    return text


def run(argv, cwd=REPO):
    printed = subprocess.list2cmdline(argv)
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    return printed, result


def main():
    lines = []
    commands = [
        # 1. The directory lit's discovery actually skips, and why (per git blame).
        ["git", "--no-pager", "show",
         "89e2f98e29c289ae8ad9e00dd310104fea9fd7df:"
         "tools/clang/test/HLSLFileCheck/lit.local.cfg"],
        ["git", "--no-pager", "show",
         "89e2f98e29c289ae8ad9e00dd310104fea9fd7df:"
         "tools/clang/test/DXILValidation/lit.local.cfg"],
        ["git", "--no-pager", "log", "--format=%H %ad %s", "--date=short",
         "--", "tools/clang/test/HLSLFileCheck/lit.local.cfg"],
        ["git", "--no-pager", "show",
         "b503da7084b4200909d2a3b7dcfc18e8d2944eec", "--stat"],

        # 2. Direct measurement: does lit actually discover any tests under
        #    HLSLFileCheck / DXILValidation? (--show-tests only enumerates,
        #    it does not invoke dxc/dxv/FileCheck, so this is read-only and
        #    needs no ground-truth ---build.)
        ["python", "utils/lit/lit.py", "--show-tests",
         "--param=build_mode=Release",
         "build/tools/clang/test/HLSLFileCheck"],
        ["python", "utils/lit/lit.py", "--show-tests",
         "--param=build_mode=Release",
         "build/tools/clang/test/DXILValidation"],

        # 3. Control: the newer, lit-discoverable migration tree exists and
        #    IS found by the same tool (proves --show-tests can find tests at
        #    all; the two empty results above are not a broken invocation).
        #    It has no "validation" subdirectory, i.e. DXIL validator tests
        #    specifically were not part of this migration.
        ["python", "-c",
         "from pathlib import Path; "
         "p = Path('tools/clang/test/HLSLFileCheckLit'); "
         "print(sorted(x.name for x in p.iterdir()))"],

        # 4. Population count: how many RUN-line test files sit in the
        #    lit-excluded validation tree, and are new ones still landing
        #    there after the exclusion (PR #5537, 2023-08-18)?
        ["git", "--no-pager", "log", "-1", "--format=%H %ad %s", "--date=short",
         "--", "tools/clang/test/HLSLFileCheck/validation/wavesize/max-too-large.ll"],

        # 5. Where are these files actually run, if not by lit? hcttest.cmd's
        #    manual, one-directory-at-a-time TAEF fallback.
        ["git", "--no-pager", "grep", "-n", "-A2",
         "ManualFileCheckTest",
         "89e2f98e29c289ae8ad9e00dd310104fea9fd7df", "--", "utils/hct/hcttest.cmd"],

        # 6. Confirm the old GoogleTest/TAEF harness does not run these .ll
        #    files either (it is a separate, hand-written C++ test).
        ["git", "--no-pager", "grep", "-c", "HLSLFileCheck",
         "89e2f98e29c289ae8ad9e00dd310104fea9fd7df", "--",
         "tools/clang/unittests/HLSL/ValidationTest.cpp"],

        # 7. Ask 3 (maintainer follow-up comment): "DXC is also missing test
        #    coverage for external validator workflows." Evidence this has
        #    since been added, and that it IS lit-discovered.
        ["git", "--no-pager", "log", "--follow", "--format=%H %ad %s", "--date=short",
         "--", "tools/clang/test/DXC/validate_1_8_2502.test"],
        ["python", "utils/lit/lit.py", "--show-tests",
         "--param=build_mode=Release",
         "build/tools/clang/test/DXC"],

        # 8. Ground-truth provenance control (same rule as every other issue
        #    in this batch): the local build self-reports a fork-local merge
        #    commit; prove its tree is identical to the cited public commit
        #    outside the triage skill directory, with a negative control
        #    that shows the same diff finding real differences elsewhere.
        ["git", "--no-pager", "diff", "--name-only",
         "7665270b9", "89e2f98e29c289ae8ad9e00dd310104fea9fd7df"],
        # CONTROL: the ground-truth ref itself is a shallow single-commit
        # fetch (no reachable ancestor), so the ancestor-based control used
        # elsewhere in this batch (<sha>~200) does not resolve here. Use an
        # old, reachable stable-release tag instead -- it must show real
        # differences outside the skill dir, proving the diff/filter above
        # can detect a difference at all and is not silently vacuous.
        ["git", "--no-pager", "diff", "--name-only",
         "v1.4.1907", "89e2f98e29c289ae8ad9e00dd310104fea9fd7df"],
    ]

    for argv in commands:
        printed, result = run(argv)
        lines.append(f"$ {printed}")
        lines.append(f"# cwd: {REPO_TOKEN}")
        lines.append(f"# exit: {result.returncode}")
        stdout = result.stdout.rstrip("\n")
        if argv[:3] == ["git", "--no-pager", "diff"]:
            files = [f for f in stdout.split("\n") if f]
            outside_skill = [
                f for f in files
                if not f.startswith(".github/skills/dxc-issue-triage/")
            ]
            lines.append(
                f"# summarised: {len(files)} total changed files; "
                f"{len(outside_skill)} outside .github/skills/dxc-issue-triage/"
            )
            shown = outside_skill[:15]
            label = "all" if len(shown) == len(outside_skill) else "first 15 of"
            lines.append(f"# files outside the skill dir ({label} {len(outside_skill)}):")
            lines.extend(shown)
        else:
            lines.append(stdout)
        if result.stderr.strip():
            lines.append("# stderr:")
            lines.append(result.stderr.rstrip("\n"))
        lines.append("")

    OUT.write_text(sanitize("\n".join(lines)), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    sys.exit(main())
