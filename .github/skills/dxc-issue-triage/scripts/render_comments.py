"""Splice the per-issue draft comments into a batch report.

Generated from issues/<nnnn>/comment.md so the report and the artifacts cannot
drift apart. Safe to re-run: it replaces the section in place.

    python scripts/render_comments.py 002

Issue numbers, titles and batch membership come from triage.db, so this does
not need editing when a new batch is triaged.
"""
import os
import re
import sqlite3
import sys

# Take the roots from triage.py rather than recomputing them: two scripts with
# their own idea of where the workspace lives is how a report ends up splicing
# drafts from a directory nobody is editing.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from triage import DB, ISSUES, REPORTS  # noqa: E402

START = "## Proposed issue comments"
END = "## Caveats"

PREAMBLE = """These are **drafts for review, not posted**. No comment, label or state change
has been made on any issue. Each is written to be postable as-is by a maintainer, and every
claim in them is backed by captured evidence in `issues/<nnnn>/`.

They deliberately avoid promising fixes or timelines, and where the next step is a product or
language decision they say so rather than pre-empting it. Quoted compiler output was
re-verified before being written down.

Each draft ends with a trailer disclosing that it came from an assisted triage pass.

Source of each is `issues/<nnnn>/comment.md` — edit there, then re-run
`scripts/render_comments.py <batch>` to refresh this section.
"""


def normalise(batch):
    """Accept '2', '002' or 'batch-002'; the db has held both conventions."""
    digits = re.sub(r"\D", "", batch) or batch
    return {batch, digits, digits.zfill(3), f"batch-{digits.zfill(3)}"}


def main():
    batch = sys.argv[1] if len(sys.argv) > 1 else "002"
    keys = normalise(batch)
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    rows = [r for r in db.execute(
        "SELECT number, title FROM issues WHERE batch IN (%s) ORDER BY number"
        % ",".join("?" * len(keys)), tuple(keys))]
    if not rows:
        sys.exit(f"no issues recorded for batch {batch!r}")

    report = os.path.join(
        REPORTS, f"batch-{re.sub(r'[^0-9]', '', batch).zfill(3)}.md")
    if not os.path.exists(report):
        cand = [os.path.join(REPORTS, f"batch-{k}.md") for k in sorted(keys)]
        report = next((c for c in cand if os.path.exists(c)), report)
    if not os.path.exists(report):
        sys.exit(f"report not found: {report}")

    parts = [START, "", PREAMBLE, ""]
    missing = []
    for r in rows:
        path = os.path.join(ISSUES, f"{r['number']:04d}", "comment.md")
        if not os.path.exists(path):
            missing.append(r["number"])
            continue
        body = open(path, encoding="utf-8").read()
        body = re.sub(r"^<!--.*?-->\s*", "", body, flags=re.S).strip()
        url = f"https://github.com/microsoft/DirectXShaderCompiler/issues/{r['number']}"
        parts += [f"### Draft — [#{r['number']}]({url}) {r['title']}", "",
                  "````markdown", body, "````", ""]
    if missing:
        sys.exit(f"no comment.md for: {missing}")

    section = "\n".join(parts).rstrip() + "\n\n---\n\n"
    text = open(report, encoding="utf-8").read()
    if START in text:
        head, _, rest = text.partition(START)
        _, _, tail = rest.partition(END)
        text = head + section + END + tail
    else:
        text = text.replace(END, section + END, 1)
    open(report, "w", encoding="utf-8").write(text)
    print(f"{os.path.basename(report)} updated: {len(rows)} draft comment(s) spliced in")


if __name__ == "__main__":
    main()
