# Method notes from #4415

Observations about the *method*, not about the issue. Kept separate from `notes.md` so the
issue write-up stays about the issue.

## 1. `; shader hash:` is not evidence that validation ran

The obvious anchor for "the validator accepted this" is the signed-container hash in `dxc`'s
disassembly, on the reasoning that a container is only signed after validation. Measured on
this repro, `dxc` prints the **same** `; shader hash: a2c70e5346dd5ea8724b1a8e8f632a87` with
and without `-Vd`. A predicate keyed on the hash's presence therefore says nothing about
whether the validator ran, and the `-Vd` capture that was supposed to be the discriminating
control is not one.

Recorded in `variant-control-vd-hash-identity-main-debug.txt`.

The replacement anchor is a shader that genuinely fails validation
(`control-validation-fails.hlsl`, adapted from `tools/clang/test/DXILValidation/rootSigDefine10.hlsl`):
it prints `error: validation errors` and exits `0x80004005`, which does prove the plain `dxc`
path validates. Prove liveness with a failure, not with an artefact of success.

## 2. For an "accepts what it should reject" issue, the control must vary one thing

The natural control set — a valid module (accepted) and a garbage module (rejected) — leaves a
hole: garbage is rejected for reasons that have nothing to do with the operand under test. The
control that actually settles it holds the **operand value** fixed and varies only the
**opcode**:

- `zeroinitializer` handle on `annotateHandle` → accepted
- `zeroinitializer` handle on `textureLoad` → `Instructions should not read uninitialized value.`

Same build, same run, same value. Nothing else can explain the difference. The mirrored pair is
worth more than any number of one-sided captures, and it is cheap: one extra four-line shader.

The complementary direction is worth building too — same *instruction*, different *operand*
(`control-badprops.ll` corrupts `annotateHandle`'s props operand and gets four errors). That
one rules out "the validator never looks at this instruction at all".

## 3. Choose the checked-opcode control by measurement, not by reading the switch

The first checked-opcode control used `cbufferLoadLegacy`, chosen from source because
`ValidateHandleArgs` covers it. It does fail — but with
`Validation failed - error code 0x80aa001d` (`DXC_E_LLVM_CAST_ERROR`) and no message, because
`GetCBufSize` does `EmitInstrError(cast<CallInst>(CbHandle), ...)` at `DxilValidation.cpp:551`
and an `undef` handle is a `Constant`. As a control it proved only "something went wrong",
which is much weaker than the rule text.

`textureLoad` produces the literal rule text. The lesson is that "this opcode reaches the
check" is a source claim, and "this opcode reports the check" is a measurement; the control
needs the second. Try two or three candidates and keep the one that prints the rule by name.

An adjacent way to shortlist candidates: `tools/clang/test/LitDXILValidation/*.ll` contains
lit tests that `CHECK` for the exact rule text. Running those through `dxv` directly confirms
in one command that the rule is live in this build, before any module is doctored.

## 4. Vacuity defence for a validator harness

`dxv` prints `Validation succeeded.` and nothing about its input, so that line is also what an
empty module, an unreadable file and a run that never happened look like. `validate.py` emits
`module-annotatehandle-calls`, `annotatehandle-res-operands`,
`annotatehandle-invalid-res-operand` and `module-requests-validator-version` into the same
capture the predicate scores, and exits non-zero with `PARSE-WARNING` when the module has no
`dx.op` call or no `annotateHandle`. The predicate requires the self-test lines *and* the
result line, so a run that measured nothing cannot score as a repro.

## 5. `dxv` uses the internal validator unless `DXC_DXIL_DLL_PATH` is set — and that is testable

`lib/DxcSupport/dxcapi.extval.cpp` (`DxcDllExtValidationLoader::InitializeForDll`) loads an
external `dxil.dll` only from an **absolute** path in `DXC_DXIL_DLL_PATH`. A `dxil.dll` sitting
next to `dxv.exe` is *not* used. The harness originally printed a `[dxil.dll beside it]` line
implying otherwise; that was wrong and is now `[external-validator] DXC_DXIL_DLL_PATH=…`.

This matters because it makes the strongest available witness reachable: the release archives
contain Microsoft's **signed** `dxil.dll`, which nothing in this repo builds. Pointing
`DXC_DXIL_DLL_PATH` at one turns "the validator I compiled has a gap" into "the validator that
gates shipping shaders has a gap".

The environment variable needs its own vacuity check, because if it were ignored every result
would still appear, produced by the internal validator. The check used here is a **version
witness**: hand the external validator a module requesting valver 1.10, which the internal
validator accepts and an older signed `dxil.dll` must refuse —
`Validator version in metadata (1.10) is not supported; maximum: (1.9).` If that line does not
appear, `signed-validator.py` reports `[WITNESS-FAILED]` and stops rather than reporting
results it cannot attribute.

Corollary: modules handed to an older signed validator must be built by a matching-era `dxc`,
so their requested valver is one it supports. `release-matrix.py` builds each release's modules
with that release's own `dxc`, which makes the versions line up by construction.

Also worth knowing: the `dxil.dll` in `build/Debug/bin` is a **local branch build**
(1.9.0.5393, `damyanp/fix-resource-struct-zero-init`, `dc2088b20-dirty`), not a shipping
validator. It must not be cited as an independent witness. A release archive's is.

## 6. Look in both release cache roots

`release-matrix.py` initially reported `not-cached` for v1.6.2112, v1.7.2308, v1.8.2502 and
v1.8.2505.1 — all four are present, under
`build/tools/clang/test/dxc_releases/<version>/<dated-dir>/bin/x64/`, where the lit release
tests unpack them, rather than under the triage cache. Four holes in a 20-row matrix, none of
them real. A related earlier claim, that `dxv.exe` first ships in v1.8.2505, is also an
artefact of scanning one root: **v1.8.2502 ships it too**.

Any script that walks releases directly should search both roots, and should say `not-cached`
only after doing so. `triage.py bisect` already resolves both, which is why bisect covered
releases the first matrix run reported as missing — a discrepancy between the two is a bug in
the script, not a gap in the cache.

## 7. Read "non-monotonic" history before recording it

`bisect --linear` reported non-monotonic history: v1.6.2104 and v1.6.2106 `no-repro`,
everything from v1.6.2112 `repro`. That reads like a fixed→regressed transition. It is not:
those two SM 6.6 preview releases lower `ResourceDescriptorHeap` to `createHandleForLib` and
are rejected by `opcode 'CreateHandleForLib' should only be used in 'Library'` — a different
rule, catching a different property, incidentally. The invalid handle is present in all three.

A `no-repro` on an old release is a claim about *why* it did not reproduce, and the reason is
in the capture. Open it. The two-word summary in the bisect table is not the finding.

## 8. Compiler Explorer banners land in the module

CE copies the source into `!dx.source.contents`, so any token in the banner appears in the DXIL
pane and can manufacture the very hit a reader is told to look for. `godbolt-note.txt` here
avoids spelling the operand for that reason — and then has to acknowledge that the *reporter's
own* comment block contains it, since `repro.hlsl` is the issue body verbatim and must stay
that way. Where the repro itself quotes the expected output, tell the reader to read the
instruction rather than to search for a string.

## 9. Reuse `triage.redact_paths()`; do not reimplement it

Any generator in an issue directory that writes a committed capture must tokenise machine
paths, and there are two ways to get it wrong that a local `text.replace(REPO, "<repo>")` will
not catch: the absolute paths handed *to* a tool as arguments (a `-Fc <abs path>` echoed by
`subprocess.list2cmdline` leaks even when the output is clean), and spellings that differ from
`REPO` only by separator, repeated separator or case.

`triage.py` exposes `redact_paths()`, which tokenises the checkout root to `<repo>`, the triage
root to `<triage>` and the release cache to `<cache>`, matching either separator, repeated
separators and any case, and is control-tested to leave `C:\Program Files\…`,
`/usr/include/stdio.h` and ordinary diagnostic text byte-identical. All four scripts here now
`sys.path.insert` the scripts directory and `import triage` to use it, rather than carrying a
second implementation of the same rule that drifts from it.

The right response to a path-gate hit is to fix the generator and regenerate, then confirm the
regeneration did not move any scored verdict — here, all 34 capture verdicts were byte-identical
before and after. Hand-editing a capture to pass the gate is falsification, not hygiene.

## 10. Small tooling frictions

- `triage.py run` names variants with `--label`, not `--variant`; `--args` replaces argv
  entirely (repeat the input filename), while `--shader` reuses `cmd.txt`.
- `--force` is needed to overwrite an existing variant capture; prefer a new `--label`.
- `triage.py godbolt` archives the previous panes as `manual-case-godbolt-verify-<hash>.txt`
  on every republish. Two banner edits leave two stale archives; delete them.
- godbolt.org returned HTTP 502 once mid-run; retrying the same command succeeded. A publish
  failure is not a compile failure.
- The `grep`/ripgrep tool silently returns zero matches under `.github/`; `Select-String`
  works. PowerShell `Select-String` has no `-Recurse` — pipe `Get-ChildItem -Recurse` into it.
- Do not read `$LASTEXITCODE` after truncating a native command through `Select-Object -First`;
  it reports the pipeline's status, not the program's.

## 11. Cross-issue observation (deliberately absent from the draft)

#6361 was closed NOT_PLANNED as "Duplicate of #4415" (damyanp, 2024-11-05); its shader reaches
the same `annotateHandle(…, zeroinitializer, …)` shape through an uninitialized `Texture2D`
struct member. #6971 ("Report error on local variables with resource binding") is adjacent but
distinct. Per the brief, cross-issue claims belong to collation, so `comment.md` says nothing
about either.
