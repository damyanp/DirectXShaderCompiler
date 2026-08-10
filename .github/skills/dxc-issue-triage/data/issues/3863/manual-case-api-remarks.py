"""Issue 3863: is the include trace *already there* during -P, one API call away?

The command-line answer to `-P ... -H` is silence. Source reading says the
trace is still produced in preprocess mode and is stored on the result object
as DXC_OUT_REMARKS ("text directed at stdout", dxcapi.h:739-740), and that the
only thing missing is that DxcContext::Preprocess() never asks for it the way
DxcContext::Compile() does (dxclib/dxc.cpp:918 vs 1005-1039).

SKILL.md is explicit that source corroboration beats an output observation, but
a claim about what the library *does* deserves a measurement, not a reading.
This drives dxcompiler.dll directly through IDxcCompiler3::Compile with ctypes
and asks the result object for DXC_OUT_REMARKS.

Three cases, so that neither a positive nor a negative can be an artefact:
  A  -P with -H          the case at issue
  B  -P without -H       control: REMARKS must NOT carry a trace, otherwise
                         case A would prove only that REMARKS always exists
  C  normal compile, -H  control: REMARKS must carry the trace, otherwise a
                         negative in A would prove only that this harness
                         cannot see REMARKS at all

A default include handler is required: passing NULL makes the file system
answer ERROR_NOT_FOUND for every #include, which would silently produce an
empty trace for reasons that have nothing to do with this issue.

Usage (from the workspace root):
    python data/issues/3863/manual-case-api-remarks.py > \
           data/issues/3863/manual-case-api-remarks.txt
"""
import ctypes
import ctypes.wintypes as wt
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
import triage  # noqa: E402

SOURCES = ("repro.hlsl", "inc-pp-a.h", "inc-pp-b.h")

DXC_OUT_REMARKS = 11
DXC_OUT_ERRORS = 2
DXC_CP_UTF8 = 65001


class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16),
                ("Data3", ctypes.c_uint16), ("Data4", ctypes.c_ubyte * 8)]

    @classmethod
    def parse(cls, s):
        s = s.replace("-", "")
        d4 = (ctypes.c_ubyte * 8)(*bytes.fromhex(s[16:32]))
        return cls(int(s[0:8], 16), int(s[8:12], 16), int(s[12:16], 16), d4)


class DxcBuffer(ctypes.Structure):
    _fields_ = [("Ptr", ctypes.c_void_p), ("Size", ctypes.c_size_t),
                ("Encoding", ctypes.c_uint32)]


CLSID_DxcCompiler = GUID.parse("73E22D93-E6CE-47F3-B5BF-F0664F39C1B0")
CLSID_DxcUtils = GUID.parse("6245D6AF-66E0-48FD-80B4-4D271796748C")
IID_IDxcCompiler3 = GUID.parse("228B4687-5A6A-4730-900C-9702B2203F54")
IID_IDxcUtils = GUID.parse("4605C4CB-2019-492A-ADA4-65F20BB7D67F")
IID_IDxcResult = GUID.parse("58346CDA-DDE7-4497-9461-6F87AF5E0659")
IID_IDxcBlobUtf8 = GUID.parse("3DA636C9-BA71-4024-A301-30CBF125305B")


def vcall(this, index, restype, argtypes, *args):
    vtbl = ctypes.cast(this, ctypes.POINTER(ctypes.c_void_p))[0]
    fn_addr = ctypes.cast(vtbl, ctypes.POINTER(ctypes.c_void_p))[index]
    proto = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return proto(fn_addr)(this, *args)


def release(this):
    if this:
        vcall(this, 2, ctypes.c_ulong, [])


def blob_text(blob):
    """UTF-8 text of an IDxcBlobUtf8 (or any IDxcBlob holding utf-8 bytes)."""
    if not blob:
        return None
    ptr = vcall(blob, 3, ctypes.c_void_p, [])
    size = vcall(blob, 4, ctypes.c_size_t, [])
    if not ptr or not size:
        return ""
    return ctypes.string_at(ptr, size).decode("utf-8", "replace").rstrip("\0")


def get_output(result, kind):
    """(present, text) for one DXC_OUT_KIND of an IDxcResult."""
    has = vcall(result, 6, ctypes.c_int, [ctypes.c_int], kind)
    if not has:
        return False, None
    blob = ctypes.c_void_p()
    name = ctypes.c_void_p()
    hr = vcall(result, 7, ctypes.c_long,
               [ctypes.c_int, ctypes.POINTER(GUID),
                ctypes.POINTER(ctypes.c_void_p),
                ctypes.POINTER(ctypes.c_void_p)],
               kind, ctypes.byref(IID_IDxcBlobUtf8),
               ctypes.byref(blob), ctypes.byref(name))
    if hr != 0:
        return True, "<GetOutput failed hr=0x%08x>" % (hr & 0xFFFFFFFF)
    text = blob_text(blob)
    release(name)
    release(blob)
    return True, text


CASES = [
    ("A  -P with -H", ["repro.hlsl", "-P", "-Fi", "api-h.i", "-H"]),
    ("B  -P no flag", ["repro.hlsl", "-P", "-Fi", "api-plain.i"]),
    ("C  compile -H", ["repro.hlsl", "-T", "ps_6_0", "-E", "main", "-H"]),
]


def main():
    exe = triage.resolve_compiler("main-debug")
    dll = os.path.join(os.path.dirname(exe), "dxcompiler.dll")
    ver = subprocess.run([exe, "--version"], capture_output=True, text=True)
    print("compiler: main-debug")
    print("dll:      %s" % triage.display_exe(dll))
    print("version:  %s" % ver.stdout.strip())
    print("api:      IDxcCompiler3::Compile, then IDxcResult::HasOutput/"
          "GetOutput(DXC_OUT_REMARKS=11)")
    print()

    work = os.path.join(HERE, "work-api-remarks")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    for s in SOURCES:
        shutil.copy(os.path.join(HERE, s), work)

    lib = ctypes.WinDLL(dll)
    create = lib.DxcCreateInstance
    create.restype = ctypes.c_long
    create.argtypes = [ctypes.POINTER(GUID), ctypes.POINTER(GUID),
                       ctypes.POINTER(ctypes.c_void_p)]

    compiler = ctypes.c_void_p()
    utils = ctypes.c_void_p()
    hr = create(ctypes.byref(CLSID_DxcCompiler),
                ctypes.byref(IID_IDxcCompiler3), ctypes.byref(compiler))
    assert hr == 0, "DxcCreateInstance(compiler) hr=0x%08x" % (hr & 0xFFFFFFFF)
    hr = create(ctypes.byref(CLSID_DxcUtils),
                ctypes.byref(IID_IDxcUtils), ctypes.byref(utils))
    assert hr == 0, "DxcCreateInstance(utils) hr=0x%08x" % (hr & 0xFFFFFFFF)

    handler = ctypes.c_void_p()
    hr = vcall(utils, 9, ctypes.c_long, [ctypes.POINTER(ctypes.c_void_p)],
               ctypes.byref(handler))
    assert hr == 0, "CreateDefaultIncludeHandler hr=0x%08x" % (hr & 0xFFFFFFFF)

    cwd = os.getcwd()
    os.chdir(work)
    src = open("repro.hlsl", "rb").read()
    rows = []
    try:
        for label, argv in CASES:
            print("== %s" % label)
            print("   args: %s" % subprocess.list2cmdline(argv))
            buf = ctypes.create_string_buffer(src, len(src))
            source = DxcBuffer(ctypes.cast(buf, ctypes.c_void_p),
                               len(src), DXC_CP_UTF8)
            arr = (ctypes.c_wchar_p * len(argv))(*argv)
            result = ctypes.c_void_p()
            hr = vcall(compiler, 3, ctypes.c_long,
                       [ctypes.POINTER(DxcBuffer),
                        ctypes.POINTER(ctypes.c_wchar_p), ctypes.c_uint32,
                        ctypes.c_void_p, ctypes.POINTER(GUID),
                        ctypes.POINTER(ctypes.c_void_p)],
                       ctypes.byref(source), arr, len(argv), handler,
                       ctypes.byref(IID_IDxcResult), ctypes.byref(result))
            print("   Compile hr=0x%08x" % (hr & 0xFFFFFFFF))
            status = ctypes.c_long(-1)
            vcall(result, 3, ctypes.c_long,
                  [ctypes.POINTER(ctypes.c_long)], ctypes.byref(status))
            print("   GetStatus=0x%08x" % (status.value & 0xFFFFFFFF))
            _, errs = get_output(result, DXC_OUT_ERRORS)
            if errs:
                print("   errors: %s" % errs.strip().replace("\n", " | ")[:200])
            present, remarks = get_output(result, DXC_OUT_REMARKS)
            text = remarks or ""
            traced = "Opening file [" in text
            print("   HasOutput(DXC_OUT_REMARKS)=%s  bytes=%d  "
                  "contains 'Opening file ['=%s" % (present, len(text), traced))
            for line in [l for l in text.splitlines()
                         if "Opening file [" in l]:
                print("   | %s" % line)
            rows.append((label, present, len(text), traced))
            release(result)
            print()
    finally:
        os.chdir(cwd)

    print("summary")
    print("%-16s %-24s %8s %-22s" % ("case", "HasOutput(REMARKS)", "bytes",
                                     "trace in REMARKS"))
    for label, present, size, traced in rows:
        print("%-16s %-24s %8d %-22s" % (label, present, size, traced))
    print()
    print("CONTROLS: B (no -H) must show no trace: %s"
          % ("PASS" if not rows[1][3] else "FAIL"))
    print("          C (compile with -H) must show a trace: %s"
          % ("PASS" if rows[2][3] else "FAIL -- harness cannot see REMARKS"))
    print("FINDING:  A (-P with -H) carries the include trace in REMARKS: %s"
          % rows[0][3])

    release(handler)
    release(utils)
    release(compiler)
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
