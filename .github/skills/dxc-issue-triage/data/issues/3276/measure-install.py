"""Measure what DXC's CMake install targets actually deposit (issue 3276).

Read-only with respect to the repository: it installs into a scratch prefix
*outside* the repo and never writes into the source tree. It echoes every
command it runs (subprocess.list2cmdline) so the capture can be re-derived
rather than trusted.

Usage:
    python measure-install.py --build <repo>/build --config Release \
                              --scratch <some dir outside the repo>

All machine paths are redacted to <repo> / <prefix> / <build> on output.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]


def redact(text, build, scratch, cmake=None):
    for real in (scratch, build, REPO):
        for form in (str(real), str(real).replace("\\", "/")):
            token = {scratch: "<prefix>", build: "<build>", REPO: "<repo>"}[real]
            text = text.replace(form, token)
    if cmake:
        for form in (str(cmake), str(cmake).replace("\\", "/")):
            text = text.replace(form, "cmake")
    return text


REDACT = {}


def run(argv, cwd=None):
    print("$ " + redact(subprocess.list2cmdline(argv), **REDACT), flush=True)
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                          errors="replace")
    return proc


def summarise(root):
    """Classify every installed file under root by install destination."""
    buckets = {}
    total = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        rel = Path(dirpath).relative_to(root).as_posix()
        for name in filenames:
            total += 1
            parts = rel.split("/") if rel != "." else []
            if not parts:
                key = "<prefix>/"
            elif parts[0] == "include":
                key = "<prefix>/include/" + (parts[1] if len(parts) > 1 else "")
            elif parts[0] in ("bin", "lib"):
                key = "<prefix>/" + parts[0] + "/"
            else:
                key = "<prefix>/" + "/".join(parts[:2]) + "/"
            buckets[key] = buckets.get(key, 0) + 1
    return total, buckets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", required=True)
    ap.add_argument("--config", default="Release")
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--component", action="append", default=[])
    ap.add_argument("--cmake", default=os.environ.get("CMAKE", "cmake"))
    ap.add_argument("--list", choices=["full", "sample", "none"], default="full",
                    help="how much of the installed file list to print")
    ap.add_argument("--label", required=True)
    args = ap.parse_args()

    build = Path(args.build).resolve()
    scratch = Path(args.scratch).resolve()
    if REPO in scratch.parents or scratch == REPO:
        sys.exit("refusing to install inside the repository")
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)

    REDACT.update(build=build, scratch=scratch, cmake=args.cmake)

    print("# label: %s" % args.label)
    print("# build: <build>  (config %s)" % args.config)
    print("# prefix: <prefix>  (scratch, outside the repository)")
    print("# components: %s" % (",".join(args.component) or "<default: all>"))
    print()

    if args.component:
        rcs = []
        for comp in args.component:
            proc = run([args.cmake, "--install", str(build), "--config", args.config,
                        "--prefix", str(scratch), "--component", comp])
            out = redact(proc.stdout, **REDACT)
            lines = out.splitlines()
            if len(lines) > 20:
                print("# %d lines of install output; first 12 and last 3 shown"
                      % len(lines))
                for line in lines[:12]:
                    print(line)
                print("...")
                for line in lines[-3:]:
                    print(line)
            else:
                for line in lines:
                    print(line)
            if proc.stderr.strip():
                print(redact(proc.stderr, **REDACT), end="")
            print("# exit: %d" % proc.returncode)
            rcs.append(proc.returncode)
        rc = max(rcs)
    else:
        proc = run([args.cmake, "--install", str(build), "--config", args.config,
                    "--prefix", str(scratch)])
        out = redact(proc.stdout, **REDACT)
        lines = out.splitlines()
        print("# %d lines of install output; first 15 and last 5 shown" % len(lines))
        for line in lines[:15]:
            print(line)
        if len(lines) > 20:
            print("...")
            for line in lines[-5:]:
                print(line)
        if proc.stderr.strip():
            print(redact(proc.stderr, **REDACT), end="")
        print("# exit: %d" % proc.returncode)
        rc = proc.returncode

    print()
    total, buckets = summarise(scratch)
    print("# installed files: %d" % total)
    for key in sorted(buckets, key=lambda k: (-buckets[k], k)):
        print("%8d  %s" % (buckets[key], key))

    print()
    if args.list != "none":
        limit = None if args.list == "full" else 8
        print("# installed files, sorted (destinations relative to the install "
              "prefix)%s:" % ("" if limit is None else
                              "; first %d per directory" % limit))
        for dirpath, _dirnames, filenames in sorted(os.walk(scratch)):
            rel = Path(dirpath).relative_to(scratch).as_posix()
            names = sorted(filenames)
            shown = names if limit is None else names[:limit]
            for name in shown:
                print("<prefix>/" + (name if rel == "." else rel + "/" + name))
            if limit is not None and len(names) > limit:
                print("<prefix>/%s/  ... and %d more"
                      % (rel, len(names) - limit))

    return rc


if __name__ == "__main__":
    sys.exit(main())
