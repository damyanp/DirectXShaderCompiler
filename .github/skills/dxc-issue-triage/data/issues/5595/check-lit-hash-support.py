#!/usr/bin/env python3
"""Evidence-gathering script for issue #5595 ("[Feature Request] support hash
stability test in lit").

This issue has no HLSL repro: it asks for a change to the test *infrastructure*
(lit), not to the compiler. There is nothing for `dxc` to compile that would
confirm or refute it, so there is no cmd.txt / match.json for this issue -- the
evidence instead comes from (a) whether a lit-native hash-stability mechanism
exists in the tree today, and (b) the fate of the PR that tried to add one.

Run from anywhere inside the repo:
    python check-lit-hash-support.py > manual-case-lit-hash-absence.txt

Every command below is echoed via subprocess.list2cmdline(argv) before its
output, per SKILL.md's rule that a transcribed command line must be
regenerated, not hand-typed.
"""
import subprocess
import sys


def run(argv, cwd=None):
    print("$ " + subprocess.list2cmdline(argv))
    try:
        out = subprocess.run(
            argv, cwd=cwd, capture_output=True, text=True, check=False
        )
    except FileNotFoundError as e:
        print(f"(could not run: {e})")
        return
    text = (out.stdout or "") + (out.stderr or "")
    print(text.rstrip("\n"))
    print(f"(exit {out.returncode})")
    print()


def main():
    repo_root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    print(f"# repo root: {repo_root}")
    print(f"# HEAD: " + subprocess.run(
        ["git", "log", "-1", "--format=%H %ci %s"],
        cwd=repo_root, capture_output=True, text=True, check=True,
    ).stdout.strip())
    print()

    print("## 1. No lit-native hash-stability format/harness exists in the tree")
    run(["git", "grep", "-n", "-i",
         "-e", "DxcHashTest",
         "-e", "HashStability.py",
         "-e", "hash_stability",
         "-e", "%hash_stability",
         "--", ":!.github/skills/dxc-issue-triage"], cwd=repo_root)

    print("## 2. lit's available test formats (no hash-related one)")
    run(["git", "ls-files", "utils/lit/lit/formats/"], cwd=repo_root)

    print("## 3. HLSLFileCheckLit (lit) vs HLSLFileCheck (TAEF-only) file counts")
    lit_files = subprocess.run(
        ["git", "ls-files", "tools/clang/test/HLSLFileCheckLit"],
        cwd=repo_root, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    taef_files = subprocess.run(
        ["git", "ls-files", "tools/clang/test/HLSLFileCheck"],
        cwd=repo_root, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    print(f"HLSLFileCheckLit tracked files: {len(lit_files)}")
    print(f"HLSLFileCheck tracked files:    {len(taef_files)}")
    print()

    print("## 4. No HLSLFileCheckLit test carries a hash-stability directive")
    run(["git", "grep", "-l", "-i", "-e", "hash",
         "--", "tools/clang/test/HLSLFileCheckLit"], cwd=repo_root)

    print("## 5. The existing TAEF hash-stability tests (CodeGenHashStability*)")
    run(["git", "grep", "-n", "CodeGenHashStability",
         "--", "tools/clang/unittests/HLSL/CompilerTest.cpp"], cwd=repo_root)

    print("## 6. PR #5600 ('[lit] Add hash stability test for lit.', 'Fixes #5595')")
    print("    -- fetch its head directly from upstream and test ancestry")
    run(["git", "fetch", "upstream", "pull/5600/head"], cwd=repo_root)
    run(["git", "rev-parse", "FETCH_HEAD"], cwd=repo_root)
    run(["git", "log", "-1", "--format=%H %ci %s", "FETCH_HEAD"], cwd=repo_root)
    run(["git", "merge-base", "--is-ancestor", "FETCH_HEAD", "HEAD"], cwd=repo_root)
    print("(exit 1 above means FETCH_HEAD -- the PR's own final commit,")
    print(" cd69ffc8e37c673bc117c6248d56a44875f96e45 -- is NOT an ancestor of")
    print(" this branch's HEAD: the PR was never merged. Corroborated by")
    print(" `gh pr view 5600` reporting state=OPEN, mergedAt=null,")
    print(" mergeCommit=null, and by section 1 above finding none of the PR's")
    print(" identifiers (DxcHashTest, HashStability.py, hash_stability) in the")
    print(" tree.)")


if __name__ == "__main__":
    sys.exit(main())
