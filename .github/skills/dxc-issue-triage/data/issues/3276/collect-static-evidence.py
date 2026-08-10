"""Static evidence for issue 3276: which install() rules exist, and where they
are platform-conditional.

Every command is echoed with subprocess.list2cmdline before it runs, so the
capture can be re-derived rather than trusted. Read-only: nothing but `git grep`
and file reads.

Usage:  python collect-static-evidence.py
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]


def redact(text):
    for form in (str(REPO), str(REPO).replace("\\", "/")):
        text = text.replace(form, "<repo>")
    return text


def run(argv, note=None):
    print()
    print("$ " + subprocess.list2cmdline(argv))
    if note:
        print("# " + note)
    proc = subprocess.run(argv, cwd=REPO, capture_output=True, text=True,
                          errors="replace")
    out = redact(proc.stdout).rstrip()
    if out:
        print(out)
    err = redact(proc.stderr).rstrip()
    if err:
        print(err)
    print("# exit: %d" % proc.returncode)
    return proc


def excerpt(relpath, first, last, note):
    print()
    lines = (REPO / relpath).read_text(encoding="utf-8",
                                       errors="replace").splitlines()
    last = min(last, len(lines))
    print("--- <repo>/%s lines %d-%d ---" % (relpath, first, last))
    print("# " + note)
    for n in range(first, last + 1):
        print("%5d| %s" % (n, lines[n - 1]))


def main():
    print("# Static evidence for #3276 'Install target installs lots of "
          "unnecessary LLVM outputs'")
    print("# Repository root redacted to <repo>. Install destinations are "
          "relative to the install prefix.")

    run(["git", "rev-parse", "HEAD"], "tree these observations describe")

    run(["git", "grep", "-c", "install(", "--", "*.cmake", "*CMakeLists.txt"],
        "files carrying install() rules")

    excerpt("CMakeLists.txt", 769, 782,
            "LLVM headers: installed unless LLVM_INSTALL_TOOLCHAIN_ONLY. "
            "No platform guard, so this applies on Linux too.")

    excerpt("tools/clang/CMakeLists.txt", 407, 420,
            "Clang headers: same single guard. This rule is what produced the "
            "487 include/clang* lines in the reporter's 2020 listing.")

    excerpt("cmake/modules/AddLLVM.cmake", 568, 586,
            "add_llvm_library(): every LLVM library gets an install() rule by "
            "default. The WIN32 branch only chooses RUNTIME vs LIBRARY.")

    excerpt("cmake/modules/AddLLVM.cmake", 680, 695,
            "add_llvm_tool(): every LLVM tool is installed unless "
            "LLVM_INSTALL_TOOLCHAIN_ONLY, in which case only llvm-ar and "
            "llvm-objdump survive - neither of which DXC builds.")

    excerpt("CMakeLists.txt", 70, 70,
            "The single knob that suppresses most of the above. Default OFF.")

    excerpt("CMakeLists.txt", 807, 825,
            "DXC's own trimmed install path: LLVM_DISTRIBUTION_COMPONENTS "
            "defaults to dxc;dxcompiler;dxc-headers and drives "
            "install-distribution. Not platform-guarded.")

    excerpt("include/dxc/CMakeLists.txt", 24, 49,
            "dxc-headers component: an explicit FILES list, so no CMakeLists.txt "
            "and no d3dx12.h reach the install tree. WinAdapter.h is added on "
            "non-Windows only.")

    excerpt("tools/clang/tools/dxcompiler/CMakeLists.txt", 155, 169,
            "dxcompiler install destination is platform-conditional: bin/ on "
            "Windows, lib/ elsewhere. This is the one place the reporter's "
            "Linux layout differs from what was measured here.")

    excerpt("gcp-pipelines/x86_64-linux-clang.yml", 36, 45,
            "DXC's own Linux CI builds its artifact with install-distribution, "
            "not with the default install target.")

    run(["git", "log", "--oneline", "--format=%h %ad %s", "--date=short",
         "-1", "4f5e4d1b7"],
        "the commit that added install-distribution to DXC")

    run(["git", "tag", "--contains", "4f5e4d1b7", "--sort=creatordate"],
        "releases carrying it (first entry = earliest tag)")

    run(["git", "log", "--oneline", "--format=%h %ad %s", "--date=short",
         "--since=2020-11-20", "--", "CMakeLists.txt", "cmake/modules/AddLLVM.cmake",
         "tools/clang/CMakeLists.txt"],
        "ABSENCE CHECK: commits touching the three files that carry the "
        "LLVM/Clang header and library install rules, since the issue was "
        "filed. Looking for any that trims the default install set.")

    run(["git", "grep", "-n", "LLVM_INSTALL_TOOLCHAIN_ONLY", "--",
         "*.cmake", "*CMakeLists.txt"],
        "every use of the suppression knob")

    run(["git", "grep", "-n", "-i", "install-distribution", "--",
         "*.md", "*.rst", "*.txt", "*.cmd", "*.sh", "*.yml"],
        "ABSENCE CHECK: is the trimmed install path documented anywhere a "
        "user would look? Only a CI file is expected to match.")

    run(["git", "ls-files", "include/dxc/Support/d3dx12.h",
         "include/dxc/CMakeLists.txt"],
        "the two things the reporter's follow-up comment names are still in "
        "the source tree (they are no longer installed)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
