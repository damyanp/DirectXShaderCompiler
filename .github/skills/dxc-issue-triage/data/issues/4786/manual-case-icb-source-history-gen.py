"""Generator for manual-case-icb-source-history.txt (#4786).

For every catalogued stable release tag (plus v1.4.1907, which predates the
dxilconv project and is expected to fail), print the exact `git show` used and
its output for the ICB-conversion line in DxbcConverter.cpp. This establishes
release history by source content rather than by executing dxc.exe, because
dxc.exe never reaches this code (see notes.md).

Run from the repository root:
    python .github/skills/dxc-issue-triage/data/issues/4786/manual-case-icb-source-history-gen.py
"""
import subprocess
import sys

TAGS = [
    "v1.4.1907", "v1.5.2003", "v1.5.2010", "v1.6.2104", "v1.6.2106",
    "v1.6.2112", "v1.7.2207", "v1.7.2212", "v1.7.2212.1", "v1.7.2308",
    "v1.8.2403", "v1.8.2403.1", "v1.8.2403.2", "v1.8.2405", "v1.8.2407",
    "v1.8.2502", "v1.8.2505", "v1.8.2505.1", "v1.9.2602", "v1.9.2602.24",
    "v1.9.2607",
]
PATH = "projects/dxilconv/lib/DxbcConverter/DxbcConverter.cpp"


def main():
    lines = [
        "# issue: 4786",
        "# generator: manual-case-icb-source-history-gen.py",
        "# purpose: establish stable-release history of the ICB float/int "
        "reinterpret-cast bug by reading source at each release tag, since "
        "dxc.exe never executes projects/dxilconv/DxbcConverter.cpp",
        "",
    ]
    for tag in TAGS:
        spec = f"{tag}:{PATH}"
        argv = ["git", "show", spec]
        lines.append(f"=== {tag} ===")
        lines.append("$ " + subprocess.list2cmdline(argv))
        p = subprocess.run(argv, capture_output=True, text=True)
        if p.returncode != 0:
            lines.append(f"[exit {p.returncode}] {p.stderr.strip()}")
            lines.append("")
            continue
        found = False
        text_lines = p.stdout.splitlines()
        for i, ln in enumerate(text_lines):
            if "ConstantDataArray::get(" in ln:
                found = True
                snippet = text_lines[max(0, i - 1):i + 3]
                lines.extend(snippet)
        if not found:
            lines.append("(ConstantDataArray::get( not found in this tag's file)")
        lines.append("")
    text = "\n".join(lines) + "\n"
    out_path = __file__.replace(
        "manual-case-icb-source-history-gen.py",
        "manual-case-icb-source-history.txt")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    sys.exit(main())
