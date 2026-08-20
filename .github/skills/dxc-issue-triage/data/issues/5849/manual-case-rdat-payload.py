"""#5849 harness: does RDAT ever indicate PAQ usage / zero the payload size?

The issue reports that DXC places no indication in RDAT of whether Payload
Access Qualifiers (PAQs) were used on a DXR any-hit/closest-hit/miss/callable
entry point, so the D3D12 runtime cannot know it may skip its
MaxPayloadSizeInBytes check. The reporter's own preferred fix, which a
maintainer agreed to, is to report RDAT's PayloadSizeInBytes as 0 for any such
entry point when PAQs are in effect.

`dxc.exe`/`-Fc` disassembly cannot answer this: the RDAT part is only produced
at container-assembly time (lib/DxilContainer/DxilContainerAssembler.cpp), not
in the LLVM IR/DXIL text a `-fcgl`/`-Fc` dump shows. `dxa.exe` (which SKILL.md
recommends trying first for reflection questions) is not present in this
checkout's build output, and this triage run may not build anything -- so this
reads the RDAT `FunctionTable` directly out of the compiled container, using
the on-disk record layout documented in
include/dxc/DxilContainer/DxilRuntimeReflection.h (container/part/table
headers) and RDAT_LibraryTypes.inl (RuntimeDataFunctionInfo field order):

    RuntimeDataFunctionInfo (all fields uint32_t, in this order):
      Name, UnmangledName, Resources, FunctionDependencies, ShaderKind,
      PayloadSizeInBytes, AttributeSizeInBytes, FeatureInfo1, FeatureInfo2,
      ShaderStageFlag, MinShaderTarget
    -> PayloadSizeInBytes sits at byte offset 20 from the start of every
       function record, and ShaderKind at byte offset 16, regardless of a
       larger RuntimeDataFunctionInfo2 stride (the base fields never move --
       that is the whole point of the documented stride-based forward/
       backward compatibility scheme).

Runs the repro's PAQ-enabled command (cmd.txt) and its
`-disable-payload-qualifiers` control against every compiler passed on the
command line, and prints each DXR entry point's ShaderKind and
PayloadSizeInBytes from the RDAT FunctionTable.

Usage:
    python manual-case-rdat-payload.py main-debug=<path to dxc.exe> \
        v1.6.2112=<path> ... > manual-case-rdat-payload-history.txt
"""

import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

SHADER_KIND_NAMES = {
    0: "Pixel", 1: "Vertex", 2: "Geometry", 3: "Hull", 4: "Domain",
    5: "Compute", 6: "Library", 7: "RayGeneration", 8: "Intersection",
    9: "AnyHit", 10: "ClosestHit", 11: "Miss", 12: "Callable", 13: "Mesh",
    14: "Amplification", 15: "Node", 16: "Invalid",
}
RDAT_PART_FOURCC = 0x54414452  # 'RDAT' little-endian uint32
FUNCTION_TABLE_PART_TYPE = 4
STRING_BUFFER_PART_TYPE = 1


def display(path):
    p = os.path.abspath(path)
    marker = os.sep + "DirectXShaderCompiler" + os.sep
    i = p.find(marker)
    return "<repo>" + p[i + len(marker) - 1:] if i >= 0 else p


def run(argv, cwd):
    shown = "$ " + subprocess.list2cmdline(
        [display(argv[0])] + [display(a) if os.path.isabs(a) else a
                               for a in argv[1:]])
    print(shown)
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                       errors="replace", timeout=120)
    text = (p.stdout or "") + (p.stderr or "")
    for line in text.splitlines():
        print("  " + line)
    print("[exit 0x%08X]" % (p.returncode & 0xFFFFFFFF))
    return p.returncode, text


def read_cstr(buf, offset):
    end = buf.find(b"\x00", offset)
    if end < 0:
        end = len(buf)
    return buf[offset:end].decode("utf-8", errors="replace")


def parse_rdat_function_table(container_bytes):
    """Returns list of dicts: name, shader_kind, payload_size, attr_size."""
    if len(container_bytes) < 32:
        return None, "container too small"
    (header_fourcc,) = struct.unpack_from("<I", container_bytes, 0)
    if header_fourcc != 0x43425844:  # 'DXBC'
        return None, "not a DXIL container (bad HeaderFourCC)"
    (part_count,) = struct.unpack_from("<I", container_bytes, 28)
    offsets = struct.unpack_from("<%dI" % part_count, container_bytes, 32)
    rdat_part_data = None
    for off in offsets:
        fourcc, size = struct.unpack_from("<II", container_bytes, off)
        data_start = off + 8
        if fourcc == RDAT_PART_FOURCC:
            rdat_part_data = container_bytes[data_start:data_start + size]
    if rdat_part_data is None:
        return None, "no RDAT part in container"

    (rdat_version, rdat_part_count) = struct.unpack_from(
        "<II", rdat_part_data, 0)
    rdat_offsets = struct.unpack_from(
        "<%dI" % rdat_part_count, rdat_part_data, 8)

    string_buffer = b""
    func_records = []
    for roff in rdat_offsets:
        (ptype, psize) = struct.unpack_from("<II", rdat_part_data, roff)
        pdata_start = roff + 8
        if ptype == STRING_BUFFER_PART_TYPE:
            string_buffer = rdat_part_data[pdata_start:pdata_start + psize]
        elif ptype == FUNCTION_TABLE_PART_TYPE:
            (record_count, record_stride) = struct.unpack_from(
                "<II", rdat_part_data, pdata_start)
            table_start = pdata_start + 8
            for i in range(record_count):
                rec_off = table_start + i * record_stride
                rec = rdat_part_data[rec_off:rec_off + record_stride]
                func_records.append(rec)

    if not func_records:
        return [], None

    results = []
    for rec in func_records:
        (name_ref, unmangled_ref, _resources, _deps, shader_kind,
         payload_size, attr_size, _feat1, _feat2, _stage_flag,
         _min_target) = struct.unpack_from("<11I", rec, 0)
        name = read_cstr(string_buffer, unmangled_ref) if string_buffer else ""
        results.append({
            "name": name,
            "shader_kind": shader_kind,
            "shader_kind_name": SHADER_KIND_NAMES.get(shader_kind,
                                                       str(shader_kind)),
            "payload_size": payload_size,
            "attr_size": attr_size,
        })
    return results, None


def measure(label, dxc_exe, extra_args, outdir):
    print("=== %s : %s ===" % (
        label, "cmd.txt" if not extra_args else " ".join(extra_args)))
    if not os.path.isfile(dxc_exe):
        print("  MISSING dxc.exe at %s" % display(dxc_exe))
        print()
        return
    rc, verbuf = run([dxc_exe, "--version"], HERE)
    container = os.path.join(
        outdir, "scratch-%s-%s.dxil" % (
            label, "disable-paq" if extra_args else "paq-default"))
    argv = [dxc_exe, "-T", "lib_6_7"] + list(extra_args) + [
        "repro.hlsl", "-Fo", container]
    rc, text = run(argv, HERE)
    if rc != 0 or not os.path.exists(container):
        print("  no container produced (invalid-probe or compile error)")
        print()
        return
    with open(container, "rb") as f:
        data = f.read()
    records, err = parse_rdat_function_table(data)
    if err:
        print("  RDAT PARSE-WARNING: %s" % err)
        print()
        return
    interesting = [r for r in records
                   if r["shader_kind_name"] in
                   ("ClosestHit", "Miss", "RayGeneration", "AnyHit",
                    "Callable")]
    if not interesting:
        print("  rdat-payload: PARSE-WARNING: 0 DXR entry-point records "
              "found (self-test failed)")
    for r in interesting:
        print("  rdat-payload: %-14s kind=%-13s PayloadSizeInBytes=%d "
              "AttributeSizeInBytes=%d" % (
                  r["name"], r["shader_kind_name"], r["payload_size"],
                  r["attr_size"]))
    print()


def main():
    outdir = os.path.join(HERE, "out")
    os.makedirs(outdir, exist_ok=True)
    compilers = []
    for arg in sys.argv[1:]:
        label, _, path = arg.partition("=")
        compilers.append((label, path))
    if not compilers:
        sys.exit("usage: manual-case-rdat-payload.py label=path/to/dxc.exe ...")

    print("#5849 RDAT payload-size-vs-PAQ history")
    print("Generated by manual-case-rdat-payload.py; do not hand-edit.")
    print()
    for label, path in compilers:
        measure(label, path, [], outdir)
        measure(label, path, ["-disable-payload-qualifiers"], outdir)


if __name__ == "__main__":
    main()
