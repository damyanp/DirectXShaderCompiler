import importlib.util
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
TRIAGE = os.path.abspath(os.path.join(HERE, "..", "..", "..", "scripts", "triage.py"))
spec = importlib.util.spec_from_file_location("triage", TRIAGE)
triage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(triage)

TAGS = [
    "v1.4.1907",
    "v1.5.2010",
    "v1.6.2104",
    "v1.6.2106",
    "v1.6.2112",
    "v1.8.2403.2",
    "v1.8.2505",
    "v1.8.2505.1",
    "v1.9.2602",
    "v1.9.2607",
]
BASE = [
    "-T", "lib_6_4", "-spirv", "-fspv-target-env=vulkan1.2",
    "-enable-16bit-types", "-HV", "2021",
]
CASES = {
    "rayquery-without-rich-debug": BASE + ["repro.hlsl"],
    "rich-debug-without-rayquery": BASE + [
        "-fspv-debug=vulkan-with-source", "control-no-rayquery.hlsl"
    ],
}


def run(argv):
    return subprocess.run(argv, cwd=HERE, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, timeout=30)


def display_command(exe, args):
    return subprocess.list2cmdline([triage.display_exe(exe)] + args)


for tag in TAGS:
    exe = triage.ensure_release(tag)
    version = run([exe, "--version"])
    print(f"=== {tag} ===")
    print(f"exe: {triage.display_exe(exe)}")
    print("version-command:", display_command(exe, ["--version"]))
    print("version-exit:", version.returncode)
    print("version:", " | ".join((version.stdout + version.stderr).splitlines()))
    for name, args in CASES.items():
        argv = [exe] + args
        result = run(argv)
        print(f"[{name}]")
        print("command:", display_command(exe, args))
        print(f"exit: {result.returncode} (0x{result.returncode & 0xffffffff:08X})")
        text = (result.stdout + result.stderr).strip()
        print("output:", text if text else "<empty>")
