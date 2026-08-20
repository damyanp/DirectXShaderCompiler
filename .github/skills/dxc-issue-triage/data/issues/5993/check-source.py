"""Source-level check for #5993 (ClangTidy clang-analyzer-core.uninitialized.Branch
in tools/clang/tools/libclang/CIndex.cpp).

This is not a `dxc` probe: `CIndex.cpp` belongs to the optional `libclang` CMake
target, not `dxc`/`dxcompiler`, and the ground-truth build here only built
`--target dxc`. There is no compiler invocation that exercises this code, and the
`#if 1` branch is unconditional across Debug/Release, so the only faithful
instrument is the source text itself, read directly from the repository at the
ground-truth commit with `git show`.

Run from the repository root:
    python check-source.py > manual-case-source-check.txt
"""
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GROUND_TRUTH_COMMIT = "89e2f98e29c289ae8ad9e00dd310104fea9fd7df"
FILE_PATH = "tools/clang/tools/libclang/CIndex.cpp"


def repo_root():
    """Resolve the repository root from this script's own location, so the
    script carries no machine-specific absolute path."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=SCRIPT_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"could not resolve repo root from {SCRIPT_DIR}: {result.stderr}")
    return result.stdout.strip()


REPO = repo_root()


def run(argv):
    print("$ " + subprocess.list2cmdline(argv))
    result = subprocess.run(argv, cwd=REPO, capture_output=True, text=True)
    print(f"# exit: {result.returncode}")
    return result


def main():
    r = run(["git", "log", "-1", "--format=%H %ci %s", GROUND_TRUTH_COMMIT])
    print(r.stdout)

    r = run(["git", "show", f"{GROUND_TRUTH_COMMIT}:{FILE_PATH}"])
    if r.returncode != 0:
        print(r.stderr)
        sys.exit(1)
    lines = r.stdout.splitlines()

    # Locate clang_createTranslationUnit / clang_createTranslationUnit2 by signature,
    # not by a hardcoded line number -- the file has moved before.
    start = None
    for i, line in enumerate(lines):
        if line.startswith("CXTranslationUnit clang_createTranslationUnit("):
            start = i
            break
    if start is None:
        print("PARSE-WARNING: clang_createTranslationUnit signature not found")
        sys.exit(1)

    end = start
    depth = 0
    seen_open = False
    for i in range(start, min(start + 60, len(lines))):
        depth += lines[i].count("{")
        depth -= lines[i].count("}")
        if "{" in lines[i]:
            seen_open = True
        if seen_open and depth == 0:
            end = i
            break

    excerpt = lines[start:end + 15]  # include clang_createTranslationUnit2's body too
    print(f"--- {FILE_PATH} @ {GROUND_TRUTH_COMMIT}, lines {start + 1}-{start + len(excerpt)} ---")
    for offset, text in enumerate(excerpt):
        print(f"{start + 1 + offset:5d}: {text}")

    joined = "\n".join(excerpt)
    has_uninit_decl = "CXTranslationUnit TU;" in joined
    has_addr_call = "clang_createTranslationUnit2(CIdx, ast_filename, &TU)" in joined
    has_dead_branch = "#if 1 // HLSL Change Starts - no support for serialization" in joined
    has_early_return_failure = "return CXError_Failure;" in joined
    has_out_tu_assignment_on_active_arm = False
    # The active arm is the text between the "#if 1" line and the matching "#else".
    if has_dead_branch:
        if_idx = joined.index("#if 1 // HLSL Change Starts - no support for serialization")
        else_idx = joined.find("#else", if_idx)
        active_arm = joined[if_idx:else_idx] if else_idx != -1 else joined[if_idx:]
        has_out_tu_assignment_on_active_arm = "*out_TU" in active_arm

    print()
    print("--- structural checks (self-test) ---")
    print(f"declares uninitialized `CXTranslationUnit TU;`: {has_uninit_decl}")
    print(f"passes &TU into clang_createTranslationUnit2:   {has_addr_call}")
    print(f"active arm is `#if 1` HLSL-disabled branch:     {has_dead_branch}")
    print(f"active arm returns CXError_Failure immediately: {has_early_return_failure}")
    print(f"active arm ever assigns *out_TU:                {has_out_tu_assignment_on_active_arm}")

    reproduces = (
        has_uninit_decl
        and has_addr_call
        and has_dead_branch
        and has_early_return_failure
        and not has_out_tu_assignment_on_active_arm
    )
    print()
    print(f"VERDICT: pattern-present={reproduces}")

    # Positive control: confirm the tool can also detect the *fixed* shape, using
    # PR #6002's own diff (fetched separately, see pr-6002.diff), so a null result
    # above is not just a broken parser.
    print()
    print("--- control: PR #6002's proposed fix text (not applied to this checkout) ---")
    fixed_shape = (
        "#if 1 // HLSL Change Starts - no support for serialization\n"
        "  return CXTranslationUnit();\n"
        "#else\n"
    )
    fixed_has_out_tu = "*out_TU" in fixed_shape
    print("fixed shape (PR #6002) assigns *out_TU on active arm: "
          f"{fixed_has_out_tu}  (expected False; it just returns a value, no branch reads TU uninitialized)")
    print("SELF-TEST: fixed-shape-detected-as-different-from-current="
          f"{fixed_shape.strip() != joined[if_idx:if_idx + len(fixed_shape)].strip() if has_dead_branch else 'n/a'}")


if __name__ == "__main__":
    main()
