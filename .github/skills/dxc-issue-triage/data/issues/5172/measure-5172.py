"""#5172 -- does IDxcIndex::ParseTranslationUnit have any mechanism to honor
a caller-supplied include handler, the way IDxcCompiler::Compile does?

Builds and runs isense5172.exe (see isense5172.cpp for the four cases) against
the registered `main-debug` dxcompiler.dll, and writes the full transcript to
manual-case-isense5172.txt.

The DLL path is read from the triage compiler registry
(.cache/compilers/main-debug.json), which `triage.py compiler` wrote; nothing
absolute is hardcoded here. Every path written into the captured artifact is
redacted to the same <cache>/<triage>/<repo> placeholders triage.py uses in
its own capture headers, so the committed file does not ship one machine's
directory layout.

Usage:
    python measure-5172.py
"""

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# data/issues/5172 -> skill root is 3 levels up, repo root 3 more.
SKILL_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REPO_ROOT = os.path.abspath(os.path.join(SKILL_ROOT, "..", "..", ".."))
CACHE_ROOT = os.path.join(SKILL_ROOT, ".cache")


def redact(text):
    # Replace only the known absolute-path roots (in both slash spellings),
    # rather than converting every backslash in the text -- the harness's
    # own " \n " line-break marker inside quoted diagnostic text is not a
    # path separator and must survive untouched.
    for root, placeholder in (
        (CACHE_ROOT, "<cache>"),
        (SKILL_ROOT, "<triage>"),
        (REPO_ROOT, "<repo>"),
    ):
        text = text.replace(root, placeholder)
        text = text.replace(root.replace("\\", "/"), placeholder)
    return text


def run_harness():
    registry_path = os.path.join(CACHE_ROOT, "compilers", "main-debug.json")
    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)
    exe_path = registry["exe_path"]
    dll_path = os.path.join(os.path.dirname(exe_path), "dxcompiler.dll")
    if not os.path.exists(dll_path):
        print("measure-5172: %s does not exist" % dll_path, file=sys.stderr)
        return 1

    harness = os.path.join(HERE, "bin", "isense5172.exe")
    if not os.path.exists(harness):
        print(
            "measure-5172: %s not built; run build-isense5172.cmd first"
            % harness,
            file=sys.stderr,
        )
        return 1

    env = dict(os.environ)
    env["DXC_5172_DLL"] = dll_path
    proc = subprocess.run(
        [harness],
        cwd=HERE,
        env=env,
        capture_output=True,
        text=True,
    )

    out_path = os.path.join(HERE, "manual-case-isense5172.txt")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# manual-case: #5172 ParseTranslationUnit vs IDxcIncludeHandler\n")
        f.write("# compiler: main-debug\n")
        f.write("# generator: measure-5172.py\n")
        f.write(
            "# command: %s\n"
            % redact(subprocess.list2cmdline([harness]))
        )
        f.write("# cwd: %s\n" % redact(HERE))
        f.write("# env DXC_5172_DLL: %s\n" % redact(dll_path))
        f.write("# exit: %d\n" % proc.returncode)
        f.write("#\n")
        f.write(redact(proc.stdout))
        if proc.stderr:
            f.write("\n# stderr:\n")
            f.write(redact(proc.stderr))

    print("wrote %s (exit %d)" % (out_path, proc.returncode))
    return 0


def git(args):
    return subprocess.run(
        ["git"] + args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def run_source_evidence():
    """Write manual-case-source-evidence.txt: the git/grep commands behind
    every source claim in notes.md, each echoed and each with its output.

    Two commands search for something known to be there first (the
    IDxcIncludeHandler parameter on the Compile overloads) before searching
    for its absence on ParseTranslationUnit -- an absence is only evidence
    once the same tool is shown able to find a presence.
    """
    out_path = os.path.join(HERE, "manual-case-source-evidence.txt")
    lines = []
    lines.append("#5172 -- the source behind the measurement")
    lines.append("")
    lines.append(
        "Produced by `python measure-5172.py --source`, run from a checkout"
    )
    lines.append("of the repo this file lives in. Every command is echoed exactly as")
    lines.append("executed; re-run any of them yourself.")
    lines.append("")

    def section(title, cmd_args, cwd_note=""):
        lines.append("=" * 78)
        lines.append(title)
        lines.append("-" * 78)
        cmdline = "git " + subprocess.list2cmdline(cmd_args)
        lines.append("$ %s%s" % (cmdline, cwd_note))
        r = git(cmd_args)
        lines.append("(exit %d)" % r.returncode)
        text = (r.stdout or "") + (r.stderr or "")
        lines.append(redact(text.rstrip("\n")))
        lines.append("")

    section(
        "CONTROL: both IDxcCompiler::Compile and IDxcCompiler3::Compile DO "
        "take an IDxcIncludeHandler (so the search tool can find a "
        "presence, not just report an absence)",
        [
            "grep", "-n", "-B3", "-A1", "IDxcIncludeHandler",
            "--", "include/dxc/dxcapi.h",
        ],
    )

    section(
        "SUBJECT: IDxcIndex::ParseTranslationUnit's full parameter list -- "
        "no IDxcIncludeHandler parameter appears anywhere in it",
        [
            "grep", "-n", "-A8",
            "virtual HRESULT STDMETHODCALLTYPE ParseTranslationUnit",
            "--", "include/dxc/dxcisense.h",
        ],
    )

    section(
        "SUBJECT: the implementation unconditionally binds to a disk "
        "filesystem, with a TODO predating this issue",
        [
            "grep", "-n", "-B4", "-A6",
            "HRESULT DxcIndex::ParseTranslationUnit",
            "--", "tools/clang/tools/libclang/dxcisenseimpl.cpp",
        ],
    )

    section(
        "History: when did that TODO/MSFileSystem-only implementation "
        "first appear? (repo-wide -S search, not scoped to the current "
        "path, per SKILL.md's #2952 lesson about path moves)",
        [
            "log", "-S", "until an interface to file access is defined",
            "--all", "--format=%H %ad %s", "--date=short",
            "--", "tools/clang/tools/libclang/dxcisenseimpl.cpp",
        ],
    )

    section(
        "CONTROL: origin/main is shallow-grafted at a 2025-06-03 boundary "
        "(see .git/shallow), so this file shows as \"new file\" there and "
        "an ancestry check against it is expected to say false -- that is "
        "the graft artifact, not a real disagreement (confirmed next)",
        [
            "merge-base", "--is-ancestor",
            "6ee4074a4b43fa23bf5ad27e4f6cafc6b835e437^{commit}", "origin/main",
        ],
    )

    section(
        "The real check: is the first commit an ancestor of the oldest "
        "stable release tag, fetched with deep history from `upstream`? "
        "(exit 0 expected -- this is the genuine, ungrafted answer)",
        [
            "merge-base", "--is-ancestor",
            "6ee4074a4b43fa23bf5ad27e4f6cafc6b835e437^{commit}",
            "refs/tags/v1.4.1907",
        ],
    )

    section(
        "Confirm v1.4.1907 predates the issue (filed 2023-04-23)",
        ["log", "-1", "--format=%H %ad %s", "--date=short", "refs/tags/v1.4.1907"],
    )

    section(
        "The 2025-06-03 commit found by -S is the shallow graft's own "
        "\"new file\" boundary, not a real edit -- confirm the whole file "
        "appears as added, not modified, in that commit",
        [
            "show", "--stat", "8a8b29f967b5925a970949984442b3783d730551",
            "--", "tools/clang/tools/libclang/dxcisenseimpl.cpp",
        ],
    )

    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote %s" % out_path)
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--harness", action="store_true")
    parser.add_argument("--source", action="store_true")
    args = parser.parse_args()
    if not args.harness and not args.source:
        args.harness = True
        args.source = True

    rc = 0
    if args.harness:
        rc = run_harness() or rc
    if args.source:
        rc = run_source_evidence() or rc
    return rc


if __name__ == "__main__":
    sys.exit(main())
