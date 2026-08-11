"""Read back the recorded verdict for issue 4520 (read-only).

    python data\\issues\\4520\\manual-case-verdict-readback.py \\
        > data\\issues\\4520\\manual-case-verdict-readback.txt
"""
import os
import sqlite3
import sys

sys.path.insert(0, "scripts")
import triage  # noqa: E402

QUERY = "SELECT * FROM issues WHERE number = 4520"


def main():
    print(f"db:    {triage.redact_paths(os.path.abspath(triage.DB))}")
    print(f"query: {QUERY}\n")
    con = sqlite3.connect(f"file:{triage.DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    row = con.execute(QUERY).fetchone()
    con.close()
    for k in row.keys():
        v = row[k]
        v = "" if v is None else str(v)
        print(f"--- {k}\n{triage.redact_paths(v)}\n")


if __name__ == "__main__":
    main()
