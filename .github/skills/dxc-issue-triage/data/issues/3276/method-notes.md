# Method notes — #3276 (first build-system issue in this pass)

Everything below is about *method*, not about #3276's outcome. Sorted with the
generalisable things first.

## 1. A build-system issue has an instrument; it just isn't the compiler

The skill's machinery assumes one `dxc` invocation over one shader, scored by a
predicate. None of that applies here — and the temptation is to conclude the
issue is unverifiable and stop at code reading. It isn't. CMake generates a
complete, machine-readable description of what `install` will do:
`<build>/**/cmake_install.cmake`, one per subdirectory (164 in the existing tree,
175 in a `PredefinedParams` configure). Parsing those gives the *whole* install
set. So `not-compiler-verifiable` should not be read as "static analysis only";
it means the compiler is the wrong instrument, and the right one still needs to
be run.

**Enumerating the rules beats running the install.** Both real
`cmake --install` runs aborted mid-way — `file INSTALL cannot find
.../llvm-as.exe` — because a shared build tree has not built every target in
every configuration. A real install therefore yields a *lower bound* that
silently looks like a complete answer. The rule enumeration is unaffected by
what happens to have been built.

## 2. Configure-only A/B is cheap and turns code reading into measurement

The strongest evidence in this triage came from configuring two extra trees with
exactly one CMake variable different and **building neither**. Configure is
~2 minutes each; the install rules are fully determined at generate time. That
converted "there is an option that looks like it would help" into a table of
measured deltas, including the four places where the option *doesn't* help —
which is the part a code-reader would most likely miss (a second, unguarded
`install(DIRECTORY include/clang-c)` sitting two lines below the `endif()`).

Preconditions worth knowing before trying it:

* Use the repo's own cache file (`cmake/caches/PredefinedParams.cmake`, via
  `-C`) rather than hand-picking `-D`s. It is what DXC ships for \*nix, so it is
  both closer to a Linux reporter's configuration and not a set of options
  invented by the triager.
* Configure writes nothing into the source tree — verified with `git status`
  after both runs. It does run `nuget install` for WARP into the *build* tree.
* Put the trees outside the repository. They are ~50 MB each after configure.

## 3. Don't manufacture a predicate to satisfy the file layout

`match.json` and `cmd.txt` were deliberately not written. Any predicate over
compiler output here would be one that cannot fail, which is worse than none.
Checked before deciding: `audit_issue` (`scripts/triage.py:2083`) requires
`expected.md`, `notes.md`, `comment.md`, `triaged_by`, and godbolt-url-or-skip —
not a predicate, and not a `.hlsl`. So the layout does not force the issue. That
seems worth stating in SKILL.md, because the pressure to write a hollow
`match.json` comes entirely from the directory looking incomplete without one.

**Replace the integrity check rather than dropping it.** The value of
`match.json` is not the verdict, it is that a broken harness gets caught. Here
that role is carried by a self-test inside the analysis script:
`enumerate-install-rules.py` prints `# RULE-PARSE-SELFTEST=pass` only if the
parser recovers the three distribution components with the destinations a real
`cmake --install --component` produced. Without it, a parser bug and "this build
has no install rules" print identically. It caught a real defect: the first,
line-based version of the parser silently missed every multi-line
`file(INSTALL ...)` block, which is most of them.

## 4. Pre-registered predicates still work when the instrument changes

`expected.md` was written before investigating, with five symptom predicates
about the *install tree* rather than about compiler output. Three held, two
failed, and one of the failures (S5) split cleanly into "fails on *supported*,
holds on *documented*" — which is exactly the distinction that decided the
verdict. Pre-registration is not compiler-specific and should be described in
SKILL.md as a general step, not one about shaders.

## 5. Small traps

* `cmake` is not on `PATH` on this machine; it is under the Visual Studio
  install (`.../Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin`).
  `measure-install.py` takes a `--cmake` flag rather than assuming.
* With a multi-config generator every component shows *4* rules — one
  `file(INSTALL)` per configuration. Counting rules is not counting files.
* `shutil.rmtree` on a scratch prefix can fail with `PermissionError
  [WinError 32]` on a `.lib` another process still holds. Use a fresh scratch
  subdirectory rather than retrying the delete.
* A real `cmake --install` writes `install_manifest.txt` into the *build* dir
  using an absolute path. Harmless here (gitignored), but it means a real
  install is not a read-only operation on the build tree.
* PowerShell has no heredoc, so `python - <<'PY'` fails. Write the script to a
  file in the issue directory — which is better anyway, since the captures
  should be re-derivable.

## 6. Incidental observation, deliberately not built on

`git grep` for an unrelated string surfaced `data/issues/3686/`, which also
touches Linux packaging. No cross-issue claim is made here — per SKILL.md that
is collation's call — but if collation is looking for clusters, "Linux
build/packaging" may be one.

## 7. Suggestion for SKILL.md

A short section on non-shader issues would have saved most of the first hour:
*the artifact under test may be a build tree, an install prefix or a package,
and the same discipline applies — pre-register the symptom, measure it with the
tool that actually produces it, keep a self-test in the harness, and prefer a
controlled A/B over reading the code.* The existing "`not-compiler-verifiable`
is a legitimate outcome" wording is correct but reads as permission to stop
investigating, which is the wrong lesson.
