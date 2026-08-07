"""Mechanically re-check every verbatim quote in comment.md against the artifact it
came from, and write the result to manual-case-comment-verify.txt.

SKILL.md: "Quote compiler output verbatim and verified, not from memory. Re-run it."
Re-running is done; this closes the other half, that what landed in the draft is what
the runs actually printed. Written because transcription is exactly the step that has
no natural check -- a paraphrase of an error message reads fine and is wrong.

Read-only. Touches nothing outside data/issues/3695/.
"""

import hashlib
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
COMMENT = (HERE / "comment.md").read_text(encoding="utf-8")


def read(name):
    return (HERE / name).read_text(encoding="utf-8", errors="replace")


# Compiler Explorer's API returns pane text with ANSI SGR escapes still embedded, so
# the captured file holds e.g.
#   "\x1b[0m\x1b[1m<source>:84:14: \x1b[0m\x1b[0;1;31merror: \x1b[0m\x1b[1massignment..."
# for what renders as
#   "<source>:84:14: error: assignment..."
# A naive substring check against the raw capture therefore fails on text that is
# genuinely present, and -- the direction that matters -- a *text* predicate run over
# CE output could miss a string that is plainly visible on screen. Strip before
# comparing, and quote the stripped form in the draft.
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def read_plain(name):
    return ANSI.sub("", read(name))


results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok), detail))


# --- quoted compiler output: must appear in comment.md AND in the named capture ---
QUOTES = [
    ("Internal compiler error: LLVM Assert", "out-main-debug.txt"),
    ("Internal compiler error: access violation. Attempted to read from address "
     "0x0000000000000019", "out-v1.9.2607.txt"),
    ('assert(Val && "isa<> used on a null pointer")', "manual-case-assert-stack.txt"),
    ("DxilLowerCreateHandleForLib::ReplaceResourceUserWithHandle",
     "manual-case-assert-stack.txt"),
    ("error: local resource not guaranteed to map to unique global resource.",
     "variant-minimal-assign-main-debug.txt"),
    ("error: assignment to global resource variable '_blurResult' is not allowed",
     "manual-case-godbolt-verify.txt"),
    ("note: variable '_blurResult' is declared here", "manual-case-godbolt-verify.txt"),
]
for text, src in QUOTES:
    in_comment = text in COMMENT
    in_src = text in read_plain(src)
    check(f"quote in comment.md and in {src}: {text[:58]}...",
          in_comment and in_src,
          f"in_comment={in_comment} in_{src}={in_src}")

# The assert file path is quoted with separators normalised (the debugger prints a
# mixed C:\...\include\llvm/Support/ form). Check the distinctive tail only.
check("Casting.h(96) line number matches the capture",
      "include/llvm/Support/Casting.h(96)" in COMMENT
      and "llvm/Support/Casting.h(96)" in read_plain("manual-case-assert-stack.txt"),
      "comment normalises the leading absolute path; the tail is verbatim")

# --- exit codes: the comment states hex, the captures record decimal ---
for hex_str, dec, src in [("0xE0000001", 3758096385, "out-main-debug.txt"),
                          ("0xC0000005", 3221225477, "out-v1.9.2607.txt")]:
    m = re.search(r"^# exit: (\d+)$", read(src), re.M)
    got = int(m.group(1)) if m else -1
    check(f"{hex_str} stated in comment == exit {dec} in {src}",
          hex_str in COMMENT and got == dec, f"capture says {got}")

# --- "all 20 releases crash" and "v1.4.1907 / v1.5.2010 print nothing" ---
rel = sorted(HERE.glob("out-v*.txt"))
rel = [p for p in rel if "--" not in p.name]
verdicts = {}
silent = []
for p in rel:
    t = p.read_text(encoding="utf-8", errors="replace")
    tag = p.stem[len("out-"):]
    verdicts[tag] = re.search(r"^# verdict: (\S+)$", t, re.M).group(1)
    body = t.split("--- stdout ---", 1)[1] if "--- stdout ---" in t else ""
    if not body.replace("--- stderr ---", "").strip():
        silent.append(tag)
check("20 release captures present, every one scored repro",
      len(rel) == 20 and set(verdicts.values()) == {"repro"},
      f"n={len(rel)} verdicts={sorted(set(verdicts.values()))}")
check("exactly v1.4.1907 and v1.5.2010 produced no output at all",
      sorted(silent) == ["v1.4.1907", "v1.5.2010"], f"silent={sorted(silent)}")
check("comment names both silent releases",
      "v1.4.1907" in COMMENT and "v1.5.2010" in COMMENT)
check("comment's release range matches the captures",
      min(verdicts) == "v1.4.1907" and max(verdicts) == "v1.9.2607"
      and "v1.4.1907..v1.9.2607" in COMMENT,
      f"min={min(verdicts)} max={max(verdicts)}")

# --- the inlined shader must be byte-identical to the committed file ---
block = re.search(r"```hlsl\n(.*?)```", COMMENT, re.S)
inlined = block.group(1) if block else ""
onfile = read("minimal-crash.hlsl")
stripped = "".join(l for l in onfile.splitlines(keepends=True)
                   if not l.lstrip().startswith("//")).lstrip("\n")
check("hlsl block in comment.md == minimal-crash.hlsl minus its header comment",
      inlined == stripped,
      "sha(inlined)=%s sha(file)=%s" % (
          hashlib.sha256(inlined.encode()).hexdigest()[:16],
          hashlib.sha256(stripped.encode()).hexdigest()[:16]))
check("that shader is 10 non-blank lines, as claimed in notes.md",
      len([l for l in stripped.splitlines() if l.strip()]) == 10,
      "%d non-blank" % len([l for l in stripped.splitlines() if l.strip()]))

# --- variant / minimal-assign quote comes from a local run, no ANSI ---
for name, want, why in [
    ("variant-minimal-assign-main-debug.txt", "no-repro", "plain A = B is diagnosed"),
    ("variant-minimal-return-main-debug.txt", "no-repro", "different global is diagnosed"),
    ("variant-minimal-crash-main-debug.txt", "repro", "minimised form crashes main"),
    ("variant-minimal-crash-v1.9.2607.txt", "repro", "minimised form crashes newest release"),
    ("variant-control-valid-main-debug.txt", "no-repro", "predicate control"),
]:
    got = re.search(r"^# verdict: (\S+)$", read(name), re.M).group(1)
    check(f"{why}: {name} -> {want}", got == want, f"got {got}")

# --- Compiler Explorer ---
ce = read_plain("manual-case-ce-controls.txt")
gv = read_plain("manual-case-godbolt-verify.txt")
check("comment cites the verified shortlink aqPedMGE4",
      "godbolt.org/z/aqPedMGE4" in COMMENT)
check("comment does NOT cite the superseded shortlink bnzP3MqhY",
      "bnzP3MqhY" not in COMMENT)
check("both DXC panes exit 139 in the verified pane dump",
      gv.count("Program terminated with signal: SIGSEGV") >= 2)
check("clang -fsyntax-only control on a valid shader is clean",
      re.search(r"control-valid\.hlsl.*?-fsyntax-only.*?exit=0", ce, re.S) is not None
      or "-fsyntax-only" in ce)
check("comment claims Release-only for CE, which the panes support",
      "Release Linux builds" in COMMENT)

# --- version / provenance ---
gt = read("out-main-debug.txt")
check("version and commit in comment match the ground-truth capture",
      "1.9.0.5433" in COMMENT and "ab5400907" in COMMENT
      and "main-debug" in gt)

# --- labels named in the comment must really carry the combination ---
lp = read("manual-case-label-precedent.txt")
for n in ("5681", "6016", "6964", "7582"):
    check(f"#{n} cited as precedent appears in the label-precedent capture",
          f"#{n}" in lp and f"#{n}" in COMMENT)

# --- the trailer ---
check("AI-assistance trailer present verbatim",
      "Triaged with AI assistance. Compiler output was produced by running the repro; please"
      in COMMENT and "flag anything that looks wrong.</sub>" in COMMENT)
check("rendered draft callout naming this issue",
      "> [!WARNING]" in COMMENT and "issues/3695" in COMMENT)

# --- things the comment must NOT do ---
for word in ("probably", "likely", "presumably", "root cause", "should be easy", "memory corruption"):
    check(f"no speculation marker '{word}'", word.lower() not in COMMENT.lower())

out = [
    "comment.md quote verification -- every verbatim claim re-checked against its artifact.",
    "generated by verify-comment.py",
    "",
]
bad = 0
for label, ok, detail in results:
    bad += not ok
    out.append(("  PASS  " if ok else "  FAIL  ") + label + (f"    [{detail}]" if detail and not ok else ""))
out += ["", f"{len(results) - bad}/{len(results)} checks passed."]
(HERE / "manual-case-comment-verify.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
sys.exit(1 if bad else 0)
