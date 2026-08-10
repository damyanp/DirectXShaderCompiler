"""Enumerate every install rule DXC's configured build tree would execute (issue 3276).

Reads the generated `cmake_install.cmake` scripts in a configured build tree and
reports, per install component, the destination and the files/directories each
rule deposits. This is complete regardless of which targets happen to have been
built, which a real `cmake --install` is not: the install script aborts at the
first artifact that is missing.

Read-only. Nothing is installed and nothing in the build tree is modified.

Usage:
    python enumerate-install-rules.py --build <repo>/build
"""

import argparse
import re
import sys
from collections import OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]

COMPONENT_RE = re.compile(
    r'if\(CMAKE_INSTALL_COMPONENT STREQUAL "([^"]+)"|'
    r'if\(NOT CMAKE_INSTALL_COMPONENT OR CMAKE_INSTALL_COMPONENT STREQUAL "([^"]+)"')


def redact(text, build):
    for real, token in ((str(build), "<build>"), (str(REPO), "<repo>")):
        text = text.replace(real, token).replace(real.replace("\\", "/"), token)
    return text


def parse(path, build):
    """Yield (component, destination, type, [basenames], files_matching)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    pos = 0
    component = None
    while True:
        idx = text.find("file(INSTALL DESTINATION", pos)
        if idx < 0:
            return
        # nearest preceding component guard
        head = text[:idx]
        cm = None
        for m in COMPONENT_RE.finditer(head):
            cm = m
        component = (cm.group(1) or cm.group(2)) if cm else None
        # balanced-paren scan for the whole call
        depth = 0
        end = idx
        for i in range(text.find("(", idx), len(text)):
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        call = text[idx:end]
        pos = end
        m = re.search(r'DESTINATION "\$\{CMAKE_INSTALL_PREFIX\}/([^"]*)"', call)
        if not m:
            continue
        dest = m.group(1)
        tm = re.search(r"TYPE (\w+)", call)
        kind = tm.group(1) if tm else "?"
        names = []
        for f in re.findall(r'"([A-Za-z]:[^"]+)"', call):
            names.append(f.replace("\\", "/").rsplit("/", 1)[-1])
        yield component or "Unspecified", dest, kind, names, "FILES_MATCHING" in call


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", required=True)
    args = ap.parse_args()
    build = Path(args.build).resolve()

    scripts = sorted(build.rglob("cmake_install.cmake"))
    print("# build tree: <build>")
    print("# cmake_install.cmake scripts found: %d" % len(scripts))
    print()

    rules = []
    for s in scripts:
        for comp, dest, kind, names, matching in parse(s, build):
            rules.append((comp, dest, kind, names, matching,
                          redact(str(s.relative_to(build)).replace("\\", "/"), build)))

    by_comp = OrderedDict()
    for comp, dest, kind, names, matching, src in rules:
        by_comp.setdefault(comp, []).append((dest, kind, names, matching, src))

    # Self-test: the parser must recover the three distribution components with
    # the destinations a real `cmake --install --component <name>` produced
    # (see manual-case-install-distribution.txt). A parser that silently found
    # nothing would otherwise look identical to a build with no install rules.
    checks = {
        "dxc": ("bin", {"dxc.exe", "dxc"}),
        "dxcompiler": ("bin", {"dxcompiler.dll", "libdxcompiler.so"}),
        "dxc-headers": ("include/dxc",
                        {"config.h", "dxcapi.h", "dxcerrors.h", "dxcisense.h"}),
    }
    failures = []
    for comp, (dest, expect) in checks.items():
        got = set()
        for d, _k, names, _m, _s in by_comp.get(comp, []):
            if d == dest:
                got |= set(names)
        if not got & expect:
            failures.append("%s -> <prefix>/%s expected one of %s, got %s"
                            % (comp, dest, sorted(expect), sorted(got)))
    print("# RULE-PARSE-SELFTEST=%s%s"
          % ("pass" if not failures else "FAIL",
             "" if not failures else "  " + "; ".join(failures)))
    print()

    print("# install rules per component (a component is what "
          "`cmake --install --component <name>` selects;")
    print("#  the default `install` target runs ALL of them)")
    print()
    print("%-28s %6s  %s" % ("component", "rules", "example destinations"))
    for comp in sorted(by_comp, key=lambda c: (-len(by_comp[c]), c)):
        dests = sorted({r[0] for r in by_comp[comp]})
        print("%-28s %6d  %s" % (comp, len(by_comp[comp]),
                                 ", ".join("<prefix>/" + d for d in dests[:3])))

    print()
    print("# category summary for <prefix>/bin and <prefix>/lib "
          "(counted from the rules above, not by eye)")
    cats = {
        "lib: LLVM* archives (LLVM proper + DXC's own LLVM-style libs)":
            ("lib", lambda n: n.startswith("LLVM")),
        "lib: clang*/libclang archives":
            ("lib", lambda n: n.startswith("clang") or n.startswith("libclang")),
        "lib: SPIRV-Tools* archives":
            ("lib", lambda n: n.startswith("SPIRV-Tools")),
        "bin: LLVM developer tools":
            ("bin", lambda n: n.startswith("llvm-") or n in
             ("opt.exe", "opt", "verify-uselistorder.exe", "verify-uselistorder")),
        "bin: test binaries":
            ("bin", lambda n: "Tests" in n or n.startswith("HLSLErrors")
             or n.startswith("HLSLHost") or n.startswith("test_")
             or n.startswith("dxc_batch")),
        "bin: dxc distribution component":
            ("bin", lambda n: n in ("dxc.exe", "dxc")),
    }
    names_by_dest = {}
    for comp, dest, kind, names, matching, src in rules:
        names_by_dest.setdefault(dest, set()).update(names)
    for title, (dest, pred) in cats.items():
        hits = sorted(n for n in names_by_dest.get(dest, ()) if pred(n))
        print("%4d  %s" % (len(hits), title))
        print("      " + ", ".join(hits))
    print()
    print("# distinct file names per destination")
    for dest in sorted(names_by_dest):
        if names_by_dest[dest]:
            print("%4d  <prefix>/%s" % (len(names_by_dest[dest]), dest))

    print()
    print("# every rule, grouped by destination")
    by_dest = OrderedDict()
    for comp, dest, kind, names, matching, src in rules:
        by_dest.setdefault(dest, []).append((comp, kind, names, matching))
    for dest in sorted(by_dest):
        entries = by_dest[dest]
        print()
        print("<prefix>/%s   (%d rules)" % (dest, len(entries)))
        flat = []
        for comp, kind, names, matching in entries:
            for n in names:
                flat.append("%s%s [%s]" % (n, " (FILES_MATCHING)" if matching else "",
                                           comp))
        for item in sorted(set(flat)):
            print("    " + item)

    return 0


if __name__ == "__main__":
    sys.exit(main())
