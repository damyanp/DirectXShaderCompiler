"""#4415: does the SIGNED shipping validator accept the invalid handle too?

Everything else here uses a validator built from this working tree (a Debug
build), or the internal validator inside a release's dxcompiler.dll. Neither is
the binary that actually gates shipping shaders: that is Microsoft's signed
`dxil.dll`, which the release archives contain and which nothing in this repo
builds. If the gap #4415 describes is real, it should be visible there too --
and if it is NOT visible there, the finding is about this repo's internal
validator only, which is a materially weaker claim.

`dxv.exe` loads the internal validator out of dxcompiler.dll unless the
environment variable DXC_DXIL_DLL_PATH names an ABSOLUTE path to a dxil.dll
(lib/DxcSupport/dxcapi.extval.cpp, DxcDllExtValidationLoader::InitializeForDll).
A dxil.dll merely sitting next to dxv.exe is not used.

That creates the usual vacuity risk: if the environment variable were ignored,
every line below would still be produced, by the internal validator, and would
look identical. So the script opens with a WITNESS that can only come from the
external validator -- a module asking for validator version 1.10, which the
internal validator accepts and the older signed dxil.dll must refuse by
version. If the witness does not fire, the script says so and stops.

The subject and control modules are built by the matching release's own dxc
(see release-matrix.py) so their requested validator version is one the signed
dxil.dll supports.

Run from this directory:
    python signed-validator.py > manual-case-signed-validator.txt
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# <repo>/.github/skills/dxc-issue-triage/data/issues/4415/ -> <repo>
REPO = os.path.abspath(os.path.join(HERE, *([os.pardir] * 6)))
BIN = os.environ.get("DXC_BIN", os.path.join(REPO, "build", "Debug", "bin"))
DXV = os.path.join(BIN, "dxv.exe")

# Normalise machine paths with triage.py's own rule rather than reimplementing
# it here; it tokenises the checkout, triage and release-cache roots, matching
# either separator, repeated separators and any case.
sys.path.insert(0, os.path.join(REPO, ".github", "skills", "dxc-issue-triage",
                                "scripts"))
import triage  # noqa: E402

RELEASE = "v1.8.2505.1"
SIGNED_DIR = os.path.join(REPO, "build", "tools", "clang", "test",
                          "dxc_releases", RELEASE, "dxc_2025_07_14", "bin",
                          "x64")
SIGNED = os.path.join(SIGNED_DIR, "dxil.dll")

WITNESS = "zeroinit.ll"                                  # asks for valver 1.10
SUBJECT = os.path.join("release-modules", RELEASE + "-zeroinit.ll")
CONTROL = os.path.join("release-modules", RELEASE + "-checkedop-zeroinit.ll")


def display(path):
    return triage.redact_paths(os.path.abspath(path)).replace(os.sep, "/")


def file_version(path):
    ps = ("(Get-Item -LiteralPath '%s').VersionInfo | "
          "ForEach-Object { $_.FileVersion + ' | ' + $_.ProductVersion + "
          "' | ' + $_.CompanyName }" % path)
    p = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return p.stdout.strip() or "<unreadable>"


def run(module, env):
    print("$ set DXC_DXIL_DLL_PATH=%s" % display(env["DXC_DXIL_DLL_PATH"]))
    print("$ " + subprocess.list2cmdline([display(DXV), module]))
    p = subprocess.run([DXV, module], cwd=HERE, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    text = triage.redact_paths((p.stdout + p.stderr).strip())
    print("\n".join("  " + ln for ln in text.splitlines()) or "  <no output>")
    print("  [exit] %d -> %s" % (p.returncode,
                                 "ACCEPTED" if p.returncode == 0
                                 else "REJECTED"))
    return p.returncode, text


def main():
    print("#4415: the signed shipping validator")
    for path in (DXV, SIGNED):
        if not os.path.isfile(path):
            sys.exit("missing: %s" % display(path))
    print("[dxv]       %s" % display(DXV))
    print("[dxil.dll]  %s" % display(SIGNED))
    print("[dxil.dll]  FileVersion | ProductVersion | Company = %s"
          % file_version(SIGNED))
    print("[note] this dxil.dll comes from the %s release archive, not from "
          "this working tree; nothing here builds it." % RELEASE)

    for rel in (SUBJECT, CONTROL):
        if not os.path.isfile(os.path.join(HERE, rel)):
            sys.exit("missing module %s -- run release-matrix.py first" % rel)

    env = dict(os.environ)
    env["DXC_DXIL_DLL_PATH"] = SIGNED

    print("\n==== WITNESS: is the external validator actually being used? ====")
    print("# %s asks for validator version 1.10. The internal validator in "
          "this\n# tree accepts that; the older signed dxil.dll cannot. A "
          "version\n# complaint here is proof the environment variable took "
          "effect." % WITNESS)
    rc, text = run(WITNESS, env)
    if rc == 0 or "Validator version in metadata" not in text:
        print("\n[WITNESS-FAILED] the external validator was NOT engaged, so "
              "every result below would be the internal validator wearing a "
              "different label. Nothing further is reported.")
        return 1
    print("\n[WITNESS-OK] the signed dxil.dll is answering, not the internal "
          "validator.")

    print("\n==== CONTROL: same invalid handle on a checked opcode ====")
    print("# Must be REJECTED. If the signed validator accepted this too, the "
          "\n# subject's acceptance would say nothing about annotateHandle.")
    ctl_rc, ctl_text = run(CONTROL, env)
    if ctl_rc == 0:
        print("\n[CONTROL-FAILED] the signed validator accepted an "
              "unmistakably invalid module; the subject below proves nothing.")
        return 1
    if "Instructions should not read uninitialized value" not in ctl_text:
        print("\n[CONTROL-WARNING] rejected, but not by the rule this issue is "
              "about; read the text above before relying on it.")

    print("\n==== SUBJECT: annotateHandle with a zeroinitializer handle ====")
    sub_rc, _ = run(SUBJECT, env)

    print("\n==== verdict ====")
    print("  witness  : external signed validator engaged")
    print("  control  : textureLoad + zeroinitializer -> REJECTED")
    print("  subject  : annotateHandle + zeroinitializer -> %s"
          % ("ACCEPTED" if sub_rc == 0 else "REJECTED"))
    if sub_rc == 0:
        print("\n  The signed shipping validator applies the "
              "uninitialized-handle rule\n  to textureLoad and not to "
              "annotateHandle. #4415 is about that gap.")
    else:
        print("\n  The signed validator DOES reject it -- the gap would then "
              "be specific\n  to the validator built from this tree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
