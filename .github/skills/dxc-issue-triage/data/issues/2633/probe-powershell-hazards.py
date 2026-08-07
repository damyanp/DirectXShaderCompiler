# Hand-probe hazards in PowerShell, demonstrated
#
# Both of these corrupt a MANUAL probe only. triage.py is immune to both:
# it builds an argv list in Python and reads returncode from the process object.
#
# Run:  python probe-powershell-hazards.py > manual-case-powershell-hazards.txt

import os
import subprocess
import sys

PS = "powershell"

# Derived from this file's own location rather than hardcoded: data/issues/2633
# is six levels below the repo root. A committed script carrying one
# contributor's absolute path does not run anywhere else, and tokenising the
# literal would make it non-runnable rather than portable.
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *([os.pardir] * 6)))
DXC = os.environ.get("DXC_EXE", os.path.join(REPO, "build", "Debug", "bin", "dxc.exe"))

if not os.path.exists(DXC):
    sys.exit(f"probe-powershell-hazards: dxc not found at {DXC}; "
             f"set DXC_EXE to override")


def ps(script):
    p = subprocess.run(
        [PS, "-NoProfile", "-Command", script],
        capture_output=True, text=True,
    )
    return (p.stdout or "") + (p.stderr or "")


print("=" * 74)
print("HAZARD 1 -- an unquoted -flag=value.N token is split at the dot")
print("=" * 74)
print()
print("PowerShell's native-argument parser splits a token that starts with '-',")
print("contains '=', and then contains '.'. dxc then reports an unknown target")
print("environment, which reads exactly like a real DXC limitation.")
print()

echo = (
    r"$s = @'" "\n"
    "import sys\n"
    "print(sys.argv[1:])\n"
    r"'@; Set-Content -Path argv-echo.py -Value $s; "
)

for label, tok in [
    ("unquoted", "-fspv-target-env=universal1.5"),
    ("single-quoted", "'-fspv-target-env=universal1.5'"),
    ("unquoted -D", "-Dfoo=1.5"),
    ("no leading dash", "plain1.5"),
]:
    out = ps(echo + f"python argv-echo.py {tok}")
    print(f"  {label:<18} {tok:<34} -> {out.strip()}")

print()
print("  and what dxc says when it receives the split form:")
out = ps(
    f"& '{DXC}' -T lib_6_3 -spirv -fspv-target-env=universal1.5 lib-export.hlsl 2>&1 "
    f"| Select-String 'unknown SPIR-V target|LinkageAttributes' "
    f"| ForEach-Object {{ $_.Line.Trim() }}"
)
print("    unquoted     : " + (out.strip() or "(no match)"))
out = ps(
    f"& '{DXC}' -T lib_6_3 -spirv '-fspv-target-env=universal1.5' lib-export.hlsl 2>&1 "
    f"| Select-String 'unknown SPIR-V target|LinkageAttributes' "
    f"| ForEach-Object {{ $_.Line.Trim() }}"
)
print("    single-quoted: " + (out.strip() or "(no match)"))

print()
print("=" * 74)
print("HAZARD 2 -- $LASTEXITCODE is STALE after '| Select-Object -First N'")
print("=" * 74)
print()
print("Select-Object -First N stops the upstream pipeline early, so PowerShell")
print("never reaps the native process and $LASTEXITCODE is left holding a value")
print("that has nothing to do with the compile. The value observed varies (-1")
print("here; 0 in an interactive session where the previous statement was not a")
print("native command). Either way it is not dxc's exit code, and the 0 case")
print("means a failing compile silently reports success.")
print()

cases = [
    ("fresh shell, piped through Select-Object -First 2",
     f"& '{DXC}' -T lib_6_3 -spirv repro.hlsl 2>&1 | Select-Object -First 2 | Out-Null; \"exit=$LASTEXITCODE\""),
    ("fresh shell, no early termination",
     f"& '{DXC}' -T lib_6_3 -spirv repro.hlsl 2>&1 | Out-Null; \"exit=$LASTEXITCODE\""),
    ("fresh shell, no pipeline at all",
     f"& '{DXC}' -T lib_6_3 -spirv repro.hlsl > $null 2>&1; \"exit=$LASTEXITCODE\""),
]
for label, script in cases:
    print(f"  {label:<52} {ps(script).strip()}")

print()
print("  0x80004005 = 2147500037 unsigned = -2147467259 signed. Python's")
print("  returncode reports the unsigned form, PowerShell the signed form;")
print("  they are the same E_FAIL, which is an ordinary diagnosed error and")
print("  NOT a crash.")
