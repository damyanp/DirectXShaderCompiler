"""Generate `reports/overview.md` -- every triaged issue, ordered by actionability.

Run after every batch:

    python scripts/render_overview.py

Everything comes from triage.db, which `reindex` rebuilds from the committed
`verdict.json` files, so this cannot drift from the evidence. Nothing here is
hand-maintained; if a row looks wrong, fix the verdict and re-run.

The ordering answers "what should a maintainer do next?", which is not the same
question as "how bad is it?". An always-reproducing crash is worse than a stale
title but needs no decision -- it is already open, already labelled, and the
next step is a fix, not triage. So the tiers are about *what action is
available*, and a confirmed-still-broken issue sorts last precisely because the
triage conclusion is "nothing to do here".
"""
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(os.path.dirname(HERE), "data")
DB = os.path.join(os.path.dirname(HERE), ".cache", "triage.db")
OUT = os.path.join(ROOT, "reports", "overview.md")

REPO = "https://github.com/microsoft/DirectXShaderCompiler"

# These were deliberately selected outside the oldest-100 sweep. Keeping the
# exception set explicit prevents a recent issue from silently changing that
# progress figure.
NON_OLDEST_SWEEP = {5293, 8527, 8725, 8732, 8737}

RECENT_ACTIVITY = {
    5293: ("New external report on 2026-08-10: Release crash and Debug assert; "
           "the thread is actively watched."),
}

# (key, heading, why it sits here). Order is the report order.
TIERS = [
    ("close-fixed", "Ready to close",
     "Verified fixed, with the fixing release identified. The draft comment "
     "records the evidence; a maintainer needs only to agree and close."),
    ("needs-human-judgement", "Needs a maintainer decision",
     "Triage cannot settle these. They are blocked on a person, so they are "
     "the most actionable thing after a close."),
    ("duplicate", "Duplicate or subsumed",
     "Can be merged into another issue."),
    ("enhancement-not-bug", "Reclassify",
     "Behaving as designed. The action is relabelling and rerouting, not a "
     "fix."),
    ("needs-repro-from-reporter", "Needs the reporter",
     "Blocked on information only the reporter has."),
    ("still-valid-keep-open", "Confirmed still broken (keep open)",
     "Reproduce on current `main`. No triage action is outstanding beyond the "
     "label and title changes noted per issue."),
]


def tier_key(action):
    a = (action or "").lower()
    if a.startswith("duplicate"):
        return "duplicate"
    return a if any(a == t[0] for t in TIERS) else "still-valid-keep-open"


def batch_label(raw):
    """The db has held '002', 'batch-001' and 'batch-004'. Show one form."""
    digits = re.sub(r"\D", "", raw or "")
    return digits.zfill(3) if digits else (raw or "?")


def issue_dir(number):
    return os.path.join(ROOT, "issues", str(number))


def artifact_links(number):
    """Link only to files that exist, so the overview cannot promise a 404."""
    want = [("draft", "comment.md"), ("notes", "notes.md"),
            ("expected", "expected.md"), ("method", "method-notes.md")]
    out = []
    for label, name in want:
        if os.path.exists(os.path.join(issue_dir(number), name)):
            out.append(f"[{label}](../issues/{number}/{name})")
    return " · ".join(out) if out else "—"


def ce_cell(row):
    if row["godbolt_url"]:
        short = row["godbolt_url"].rstrip("/").rsplit("/", 1)[-1]
        return f"[{short}]({row['godbolt_url']})"
    if row["godbolt_skip"]:
        return "n/a"
    return "—"


def action_rank(row):
    """Secondary sort: within a tier, prefer rows with an action attached."""
    score = 0
    if row["text_stale"]:
        score -= 2          # the title itself needs editing
    if (row["labels_add"] or "").strip() or (row["labels_remove"] or "").strip():
        score -= 1          # labels to apply
    return (score, row["number"])


def activity_flag(number):
    return " 🔔" if number in RECENT_ACTIVITY else ""


def esc(text):
    """Keep a summary on one line and inside its table cell."""
    return " ".join((text or "").split()).replace("|", "\\|")


def main():
    if not os.path.exists(DB):
        sys.exit(f"no database at {DB}; run `triage.py reindex` first")
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = list(con.execute("SELECT * FROM issues"))
    if not rows:
        sys.exit("no issues in the database; run `triage.py reindex` first")

    by_tier = {}
    for r in rows:
        by_tier.setdefault(tier_key(r["suggested_action"]), []).append(r)
    for v in by_tier.values():
        v.sort(key=action_rank)

    batches = sorted({batch_label(r["batch"]) for r in rows})
    stale = sorted((r for r in rows if r["text_stale"]),
                   key=lambda r: r["number"])
    commits = sorted({r["triaged_with_commit"] for r in rows
                      if r["triaged_with_commit"]})

    L = []
    w = L.append
    w("<!-- GENERATED by scripts/render_overview.py -- do not edit by hand.")
    w("     Re-run after every batch; it reads triage.db, which `triage.py")
    w("     reindex` rebuilds from the committed verdict.json files. -->")
    w("")
    w("# DXC issue triage — overview")
    w("")
    w(f"**{len(rows)} issues triaged** across "
      f"{len(batches)} batches ({', '.join(batches)}). "
      "Ordered by what a maintainer can act on, most actionable first.")
    w("")
    exceptions = sorted(
        (r for r in rows if r["number"] in NON_OLDEST_SWEEP),
        key=lambda r: r["number"])
    w(f"**Oldest-100 progress: {len(rows) - len(exceptions)}/100.** "
      f"{len(exceptions)} deliberately selected issues are counted separately: "
      + ", ".join(f"[#{r['number']}]({REPO}/issues/{r['number']})"
                  for r in exceptions)
      + ".")
    w("")
    for r in sorted((r for r in rows if r["number"] in RECENT_ACTIVITY),
                    key=lambda r: r["number"]):
        w(f"> 🔔 **Recent activity — [#{r['number']}]"
          f"({REPO}/issues/{r['number']}):** "
          f"{RECENT_ACTIVITY[r['number']]}")
        w("")
    w("Nothing here has been applied. No issue has been edited, commented on, "
      "closed or relabelled; every recommendation is a proposal, and every "
      "draft comment is unposted.")
    w("")

    # ---- at a glance -------------------------------------------------
    w("## At a glance")
    w("")
    w("| Action | Issues |")
    w("| --- | ---: |")
    for key, heading, _ in TIERS:
        got = by_tier.get(key, [])
        if got:
            w(f"| [{heading}](#{anchor(heading)}) | {len(got)} |")
    w(f"| **Total** | **{len(rows)}** |")
    w("")

    if stale:
        w(f"**{len(stale)} issues whose text no longer matches their "
          "measured behaviour or artifacts.** `text_stale` is not itself a "
          "reproduction verdict: some issues below still reproduce and some "
          "do not. It means a reader following the current title, body, or "
          "thread would be led away from the measured result. Correcting that "
          "text is a cheap, immediate action.")
        w("")
        w("| # | What is stale |")
        w("| --- | --- |")
        for r in stale:
            w(f"| [#{r['number']}]({REPO}/issues/{r['number']}) "
              f"| {esc(r['text_stale'])} |")
        w("")

    # ---- tiers -------------------------------------------------------
    for key, heading, why in TIERS:
        got = by_tier.get(key, [])
        if not got:
            continue
        w(f"## {heading}")
        w("")
        w(f"*{why}*")
        w("")
        w("| # | Title | Status | History | Conf. | Repro | CE | Artifacts |")
        w("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for r in got:
            flag = " ⚠️" if r["text_stale"] else ""
            flag += activity_flag(r["number"])
            w("| [#{n}]({repo}/issues/{n}) | {t}{flag} | {st} | {h} | {c} "
              "| {q} | {ce} | {art} |".format(
                  n=r["number"], repo=REPO, t=esc(r["title"]) or "—",
                  flag=flag, st=r["status"] or "—",
                  h=esc(r["history"])[:60] or "—",
                  c=r["confidence"] or "—", q=r["repro_quality"] or "—",
                  ce=ce_cell(r), art=artifact_links(r["number"])))
        w("")
        for r in got:
            w(f"**[#{r['number']}]({REPO}/issues/{r['number']}) — "
              f"{esc(r['title'])}**  ")
            w(f"<sub>batch {batch_label(r['batch'])} · triaged against "
              f"`{(r['triaged_with_commit'] or '?')[:9]}`"
              + (f" · drafted by `{r['triaged_by']}`" if r["triaged_by"] else "")
              + (f" · reviewed by `{r['reviewed_by']}`"
                 if r["reviewed_by"] else "") + "</sub>")
            w("")
            if r["number"] in RECENT_ACTIVITY:
                w(f"> 🔔 **Recent activity.** "
                  f"{RECENT_ACTIVITY[r['number']]}")
                w("")
            if r["summary"]:
                w(esc(r["summary"]))
                w("")
            if r["text_stale"]:
                w(f"> ⚠️ **Issue text is stale.** {esc(r['text_stale'])}")
                w("")
            bits = []
            if (r["labels_add"] or "").strip():
                bits.append("add `" + "`, `".join(
                    s.strip() for s in r["labels_add"].split(",")
                    if s.strip()) + "`")
            if (r["labels_remove"] or "").strip():
                bits.append("remove `" + "`, `".join(
                    s.strip() for s in r["labels_remove"].split(",")
                    if s.strip()) + "`")
            if bits:
                w(f"*Labels:* {'; '.join(bits)}.")
                w("")
            if not r["godbolt_url"] and r["godbolt_skip"]:
                w(f"*No Compiler Explorer link:* {esc(r['godbolt_skip'])}")
                w("")
        w("")

    # ---- provenance --------------------------------------------------
    w("## Provenance and limits")
    w("")
    w("- Ground truth is a **Debug** build of `main`"
      + (f", commit `{commits[0][:9]}`" if len(commits) == 1
         else f" ({len(commits)} commits across batches)") + ". Debug matters: "
      "many older issues are asserts, which a Release build compiles out.")
    w("- **The release bisection floor is v1.4.1907** (2019-07), the oldest "
      "release shipping a usable `dxc`. For issues filed before it, "
      "\"always reproduced\" means \"for as long as it is possible to check\". "
      "SPIR-V issues have a higher floor still.")
    w("- **Compiler Explorer runs Release builds**, so a Debug-only assert "
      "looks clean there. CE corroborates the local build; it never overrules "
      "it. `dxc_trunk` is a rolling build and is not reproducible over time.")
    w("- **Sampling is deliberately unrepresentative.** Batches over-weight "
      "the oldest issues, so the verdict distribution here does not "
      "generalise to the backlog.")
    w("")
    w("Per-batch reports, including the method findings that changed how "
      "later batches were run: "
      + ", ".join(f"[batch {b}](batch-{b}.md)" for b in batches) + ".")
    w("")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L))
    counts = ", ".join(f"{k}={len(v)}" for k, v in sorted(by_tier.items()))
    print(f"overview.md written: {len(rows)} issues ({counts})")


def anchor(heading):
    """GitHub's heading-anchor rules, for the at-a-glance links."""
    a = heading.lower()
    a = a.replace("--", "").replace("`", "")
    a = re.sub(r"[^a-z0-9 -]", "", a)
    return re.sub(r"\s+", "-", a.strip()).replace("--", "-")


if __name__ == "__main__":
    main()
