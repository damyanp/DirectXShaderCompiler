"""Source-level verification for issue #5328.

Confirms the exact buggy line the issue names is still present, unchanged,
on ground truth, and that it sits in the StoreInst arm of the if/else-if
chain (not the LoadInst arm), which is what makes `LI` guaranteed-null
there. Also records `git blame` provenance. Read-only: does not modify
DXC source. Prints and records the compiler/tree identity established
earlier in this triage (main-debug @ 89e2f98e29c289ae8ad9e00dd310104fea9fd7df).
"""
import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", ".."))
TARGET_FILE = "lib/HLSL/HLMatrixBitcastLowerPass.cpp"
GROUND_TRUTH_COMMIT = "89e2f98e29c289ae8ad9e00dd310104fea9fd7df"


def run(argv):
    printed = subprocess.list2cmdline(argv)
    proc = subprocess.run(argv, capture_output=True, text=True, cwd=REPO)
    return printed, proc


def main():
    lines = []
    lines.append("# issue: 5328")
    lines.append(f"# ground-truth commit cited: {GROUND_TRUTH_COMMIT}")
    lines.append(
        "# purpose: verify the exact reported typo is still present, "
        "unchanged, at the exact location the issue names."
    )
    lines.append("")

    # 1. Show the exact lines around the reported bug.
    argv = ["git", "show", f"HEAD:{TARGET_FILE}"]
    printed, proc = run(argv)
    lines.append(f"$ {printed}")
    lines.append(f"exit: {proc.returncode}")
    src = proc.stdout
    src_lines = src.splitlines()
    # Locate the exact buggy construction.
    target = "IRBuilder<> Builder(LI);"
    hits = [i + 1 for i, l in enumerate(src_lines) if target in l]
    lines.append(f"occurrences of literal '{target}': {hits}")
    for ln in hits:
        lo, hi = max(0, ln - 12), min(len(src_lines), ln + 3)
        lines.append(f"--- context around line {ln} ---")
        for i in range(lo, hi):
            lines.append(f"{i+1}: {src_lines[i]}")
    lines.append("")

    # 2. Confirm scoping: the preceding arm binds LI via dyn_cast<LoadInst>,
    #    and the arm containing the bug binds ST via dyn_cast<StoreInst> --
    #    i.e. LI and ST are declared in sibling (mutually exclusive) arms.
    for ln in hits:
        # search upward for the two 'else if' headers bracketing this line
        window = src_lines[max(0, ln - 20):ln]
        joined = "\n".join(window)
        has_load_arm = "dyn_cast<LoadInst>" in joined
        has_store_arm = "dyn_cast<StoreInst>" in joined
        lines.append(
            f"line {ln}: preceding ~20 lines contain "
            f"dyn_cast<LoadInst> arm: {has_load_arm}, "
            f"dyn_cast<StoreInst> arm: {has_store_arm}"
        )
    lines.append("")

    # 3. git blame the exact line(s).
    for ln in hits:
        argv = ["git", "blame", "-L", f"{ln},{ln}", "--", TARGET_FILE]
        printed, proc = run(argv)
        lines.append(f"$ {printed}")
        lines.append(f"exit: {proc.returncode}")
        lines.append((proc.stdout or proc.stderr).strip())
    lines.append("")

    # 4. Confirm HEAD's tree matches the cited public ground-truth commit
    #    (established earlier in this session via a controlled diff;
    #    re-verified here for a durable, re-runnable record).
    argv = ["git", "diff", "--name-only", "HEAD", GROUND_TRUTH_COMMIT]
    printed, proc = run(argv)
    lines.append(f"$ {printed}")
    lines.append(f"exit: {proc.returncode}")
    all_diffs = [l for l in (proc.stdout or "").splitlines() if l.strip()]
    outside_skill = [l for l in all_diffs if not l.startswith(".github/skills/dxc-issue-triage/")]
    lines.append(f"files differing outside .github/skills/dxc-issue-triage/: {len(outside_skill)}")
    for l in outside_skill:
        lines.append(f"  {l}")

    text = "\n".join(lines) + "\n"
    out_path = "manual-case-source-check.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    sys.exit(main())
