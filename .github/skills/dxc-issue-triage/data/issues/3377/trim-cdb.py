"""Trim a raw cdb transcript down to the lines worth committing, for issue #3377.

Keeps case markers, command lines, assert text (Error/File/Func and the message line),
exception notices, .lastevent and stack frames. Drops loader chatter, symbol-path banners,
NatVis noise and module loads, as SKILL.md asks ("a full stack dump is noise").

Usage:  python trim-cdb.py <raw.txt>          # prints the trimmed transcript
"""

import re
import sys

KEEP = re.compile(
    r"^(###|CommandLine:|Error:\s|File:|Func:|\s+arg index|\s+#\s+Child-SP|"
    r"[0-9a-f]{2} [0-9a-f]{8}`|Last event:|\(\w+\.\w+\): |"
    r"C:\\prj\\DirectXShaderCompiler\\lib\\|C:\\prj\\DirectXShaderCompiler\\include\\)"
)
DROP = re.compile(r"^(ModLoad:|NatVis|\s*$|0:000> cdb: Reading|ntdll!LdrpDoDebuggerBreak)")


def main() -> int:
    prev_was_file = False
    with open(sys.argv[1], "r", errors="replace") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if DROP.match(line):
                prev_was_file = False
                continue
            # dxc prints the value of `File:` on the FOLLOWING line.
            if prev_was_file:
                print(line)
                prev_was_file = False
                continue
            if KEEP.match(line):
                print(line)
                prev_was_file = line.startswith("File:")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
