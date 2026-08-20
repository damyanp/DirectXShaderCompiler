"""Generator for manual-case-cmake-history.txt (issue #4766).

Echoes every command before running it, per the skill's rule that a
manual-case capture must be regenerable rather than transcribed by hand.
Run from anywhere; it invokes git against the DXC repo root via -C.
"""
import subprocess
import sys
from pathlib import Path

# Resolve the repo root relative to this file rather than hardcoding an
# absolute machine path, so the script (and its printed commands) stay
# portable across checkouts: .../<repo>/.github/skills/dxc-issue-triage/
# data/issues/4766/capture-cmake-history.py -> parents[6] is <repo>.
REPO = Path(__file__).resolve().parents[6]
OUT = Path(__file__).parent / "manual-case-cmake-history.txt"


def run(argv):
    printed = subprocess.list2cmdline(argv)
    result = subprocess.run(argv, cwd=REPO, capture_output=True, text=True)
    return printed, result


REPO_TOKEN = "<repo>"  # machine-independent stand-in, per triage.py's display_exe convention


def main():
    lines = []
    commands = [
        ["git", "--no-pager", "show", "89e2f98e29c289ae8ad9e00dd310104fea9fd7df:tools/clang/tools/dxcompiler/CMakeLists.txt"],
        ["git", "--no-pager", "log", "--follow", "--format=%H %ad %s", "--date=short",
         "-S", "add_clang_library(dxcompiler", "--",
         "tools/clang/tools/dxcompiler/CMakeLists.txt"],
        ["git", "--no-pager", "show", "89e2f98e29c289ae8ad9e00dd310104fea9fd7df:tools/clang/tools/dxildll/CMakeLists.txt"],
        ["git", "--no-pager", "log", "--format=%H %ad %s", "--date=short", "--",
         "tools/clang/tools/dxildll/CMakeLists.txt"],
        ["git", "--no-pager", "log", "-1", "--format=%H %ad %s", "--date=short", "--",
         "tools/clang/tools/dxcompiler/CMakeLists.txt"],
        ["git", "--no-pager", "grep", "-n", "LoadLibraryA",
         "89e2f98e29c289ae8ad9e00dd310104fea9fd7df", "--",
         "include/dxc/Support/dxcapi.use.h"],
        ["git", "--no-pager", "log", "-1", "--format=%H %ad %s", "--date=short",
         "89e2f98e29c289ae8ad9e00dd310104fea9fd7df"],
        ["git", "--no-pager", "diff", "--name-only",
         "7665270b9", "89e2f98e29c289ae8ad9e00dd310104fea9fd7df"],
        # CONTROL: same diff against a much older ancestor must show real
        # differences outside the skill dir, proving the check above can
        # actually detect something (SKILL.md provenance-verification rule).
        ["git", "--no-pager", "diff", "--name-only",
         "7665270b9", "89e2f98e29c289ae8ad9e00dd310104fea9fd7df~200"],
    ]
    for argv in commands:
        printed, result = run(argv)
        lines.append(f"$ {printed}")
        lines.append(f"# cwd: {REPO_TOKEN}")
        lines.append(f"# exit: {result.returncode}")
        stdout = result.stdout.rstrip("\n")
        if argv[:3] == ["git", "--no-pager", "diff"]:
            # This diff spans the whole tree (build-sha vs ground-truth-sha);
            # summarise instead of dumping every one of the ~100+ triage
            # artifact paths it touches.
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

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    sys.exit(main())
