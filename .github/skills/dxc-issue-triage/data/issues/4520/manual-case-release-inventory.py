"""Release inventory for issue 4520 -- which builds are in the history at all.

Read-only. Prints the release table triage.py bisects over, so a reader can tell
apart the three reasons a release is absent from the #4520 history:

  * prerelease=1        skipped by standing policy (this issue was filed against
                        a stable release, the December 2021 v1.6.2112, so no
                        prerelease is in scope);
  * asset=(none)        no usable dxc archive published, nothing to run;
  * probed but invalid  ran, but could not observe the symptom -- see
                        manual-case-release-history.txt, which is where the
                        v1.4.1907 / v1.5.2010 `invalid profile ps_6_6` result
                        lives.

Only the first two are decided here; the third is a measurement, not metadata.

    python data\\issues\\4520\\manual-case-release-inventory.py \\
        > data\\issues\\4520\\manual-case-release-inventory.txt
"""
import os
import sqlite3
import sys

sys.path.insert(0, "scripts")
import triage  # noqa: E402

QUERY = ("SELECT tag, published_at, bisectable, prerelease, asset_name "
         "FROM releases ORDER BY published_at")


def main():
    print(f"db:    {triage.redact_paths(os.path.abspath(triage.DB))}")
    print(f"query: {QUERY}\n")

    con = sqlite3.connect(f"file:{triage.DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(QUERY)]
    con.close()

    head = (f"{'tag':<30} {'published':<12} {'bisectable':<11} "
            f"{'prerelease':<11} asset")
    print(head)
    print("-" * len(head))
    for r in rows:
        print(f"{r['tag']:<30} {str(r['published_at'])[:10]:<12} "
              f"{r['bisectable']:<11} {r['prerelease']:<11} "
              f"{r['asset_name'] or '(none)'}")

    stable = [r for r in rows if r["bisectable"]]
    pre_with_asset = [r for r in rows if r["prerelease"] and r["asset_name"]]
    no_asset = [r for r in rows if not r["asset_name"]]

    print("\n=== summary\n")
    print(f"releases known:                {len(rows)}")
    print(f"stable and bisectable:         {len(stable)}  "
          + ", ".join(r["tag"] for r in stable))
    print(f"prerelease, skipped by policy: {len(pre_with_asset)}  "
          + ", ".join(r["tag"] for r in pre_with_asset))
    print(f"no usable dxc asset:           {len(no_asset)}  "
          + ", ".join(r["tag"] for r in no_asset))
    print("\nthe #4520 history is measured over the stable set above;")
    print("what each of those builds actually did is in")
    print("manual-case-release-history.txt and out-<tag>.txt.")


if __name__ == "__main__":
    main()
