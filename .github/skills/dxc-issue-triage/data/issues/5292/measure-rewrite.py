"""Issue 5292: dxr's -remove-unused-globals/-remove-unused-functions removes an
unused struct definition but leaves behind a typedef that names it, producing
HLSL that fails to recompile.

dxr's rewriter options (-remove-unused-globals, -remove-unused-functions, ...)
carry only Flags<[RewriteOption]> in HLSLOptions.td (not CoreOption/DriverOption),
so dxc.exe's own argument parser rejects them outright ("Unknown argument").
The real `dxr` console tool exists only as a stale Release-config binary in
this tree (build/Release/bin/dxr.exe, built long before the registered
main-debug commit) and no stable release archive ships a `dxr` executable
either (only dxc.exe/dxcompiler.dll/dxil.dll/dxv.exe) -- confirmed by listing
every cached release's bin folder. Building a Debug dxr.exe would mean
rebuilding a shared target while peers in this batch may be measuring the
shared ground-truth build, which this triage run is required not to do.

dxr.exe itself is a ~60-line wrapper (tools/clang/tools/dxr/dxr.cpp) around
one COM call: CLSID_DxcRewriter's IDxcRewriter2::RewriteWithOptions, which
*is* compiled into dxcompiler.dll -- the same dxcompiler.dll the registered
main-debug dxc.exe loads, and the same dxcompiler.dll every stable release
zip ships. So this harness calls that entry point directly through ctypes,
exactly as dxr.cpp does, without building or registering anything:

    IDxcLibrary::CreateBlobWithEncodingFromPinned   (load the source)
    IDxcRewriter2::RewriteWithOptions(source, name, argv, argc, ...)
    IDxcOperationResult::GetStatus / GetResult / GetErrorBuffer

argv is built exactly as a user's command line would appear on argv (dxr.cpp
passes the *raw* process argv, program name included, straight through to
RewriteWithOptions, which then parses it with skipArgCount=0) -- confirmed
against the stale Release dxr.exe, which reproduces the reported bug exactly
when invoked as `dxr.exe -remove-unused-functions -remove-unused-globals
-E ps_main repro.hlsl` and read back through this same argv convention.

Usage (from the workspace root):
    python data/issues/5292/measure-rewrite.py --shader repro.hlsl
    python data/issues/5292/measure-rewrite.py --history > \
           data/issues/5292/manual-case-release-history.txt
"""
import argparse
import ctypes
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
import triage  # noqa: E402

CP_UTF8 = 65001


class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16),
                ("Data3", ctypes.c_uint16), ("Data4", ctypes.c_ubyte * 8)]

    @classmethod
    def parse(cls, s):
        s = s.replace("-", "")
        d4 = (ctypes.c_ubyte * 8)(*bytes.fromhex(s[16:32]))
        return cls(int(s[0:8], 16), int(s[8:12], 16), int(s[12:16], 16), d4)


CLSID_DxcLibrary = GUID.parse("6245D6AF-66E0-48FD-80B4-4D271796748C")
IID_IDxcLibrary = GUID.parse("e5204dc7-d18c-4c3c-bdfb-851673980fe7")
CLSID_DxcRewriter = GUID.parse("b489b951-e07f-40b3-968d-93e124734da4")
IID_IDxcRewriter2 = GUID.parse("261afca1-0609-4ec6-a77f-d98c7035194e")


def vcall(this, index, restype, argtypes, *args):
    vtbl = ctypes.cast(this, ctypes.POINTER(ctypes.c_void_p))[0]
    fn_addr = ctypes.cast(vtbl, ctypes.POINTER(ctypes.c_void_p))[index]
    proto = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return proto(fn_addr)(this, *args)


def release(this):
    if this:
        vcall(this, 2, ctypes.c_ulong, [])


def blob_text(blob):
    """Raw bytes of any IDxcBlob-derived object, decoded as UTF-8.

    GetBufferPointer/GetBufferSize sit at vtable index 3/4 on every
    IDxcBlob-derived interface (IDxcBlobEncoding, IDxcBlobUtf8, the plain
    IDxcBlob returned by GetResult/GetErrorBuffer), so this is safe to reuse
    for all of them without knowing the concrete type.
    """
    if not blob:
        return None
    ptr = vcall(blob, 3, ctypes.c_void_p, [])
    size = vcall(blob, 4, ctypes.c_size_t, [])
    if not ptr or not size:
        return ""
    return ctypes.string_at(ptr, size).decode("utf-8", "replace").rstrip("\0")


def create_instance(lib, clsid, iid):
    create = lib.DxcCreateInstance
    create.restype = ctypes.c_long
    create.argtypes = [ctypes.POINTER(GUID), ctypes.POINTER(GUID),
                       ctypes.POINTER(ctypes.c_void_p)]
    out = ctypes.c_void_p()
    hr = create(ctypes.byref(clsid), ctypes.byref(iid), ctypes.byref(out))
    if hr != 0:
        raise RuntimeError("DxcCreateInstance failed hr=0x%08x" % (hr & 0xFFFFFFFF))
    return out


def rewrite(dll_path, source_text, source_name, argv):
    """Run IDxcRewriter2::RewriteWithOptions(source_text, argv) through dll_path.

    argv must include the (unused, placeholder-only) program name at [0], to
    match exactly what dxr.cpp passes through from the real process argv --
    see the module docstring.

    Returns (call_hr, status_hr, output_text_or_None, error_text_or_None).
    """
    lib = ctypes.WinDLL(dll_path)
    library = create_instance(lib, CLSID_DxcLibrary, IID_IDxcLibrary)
    rewriter = create_instance(lib, CLSID_DxcRewriter, IID_IDxcRewriter2)

    data = source_text.encode("utf-8")
    buf = ctypes.create_string_buffer(data, len(data))
    src_blob = ctypes.c_void_p()
    hr = vcall(library, 6, ctypes.c_long,
               [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32,
                ctypes.POINTER(ctypes.c_void_p)],
               ctypes.cast(buf, ctypes.c_void_p), len(data), CP_UTF8,
               ctypes.byref(src_blob))
    if hr != 0:
        release(rewriter)
        release(library)
        raise RuntimeError("CreateBlobWithEncodingFromPinned hr=0x%08x" % (hr & 0xFFFFFFFF))

    arr = (ctypes.c_wchar_p * len(argv))(*argv)
    result = ctypes.c_void_p()
    call_hr = vcall(
        rewriter, 6, ctypes.c_long,
        [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_wchar_p),
         ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p,
         ctypes.POINTER(ctypes.c_void_p)],
        src_blob, source_name, arr, len(argv), None, 0, None,
        ctypes.byref(result))

    out_text = None
    err_text = None
    status = ctypes.c_long(-1)
    if call_hr == 0 and result:
        vcall(result, 3, ctypes.c_long, [ctypes.POINTER(ctypes.c_long)],
              ctypes.byref(status))
        out_blob = ctypes.c_void_p()
        vcall(result, 4, ctypes.c_long, [ctypes.POINTER(ctypes.c_void_p)],
              ctypes.byref(out_blob))
        out_text = blob_text(out_blob)
        release(out_blob)
        err_blob = ctypes.c_void_p()
        vcall(result, 5, ctypes.c_long, [ctypes.POINTER(ctypes.c_void_p)],
              ctypes.byref(err_blob))
        err_text = blob_text(err_blob)
        release(err_blob)
        release(result)

    release(src_blob)
    release(rewriter)
    release(library)
    return call_hr, status.value, out_text, err_text


ARGV = ["dxr.exe", "-remove-unused-functions", "-remove-unused-globals",
        "-E", "ps_main"]


def classify(out_text):
    """(struct_present, typedef_present) structural read of the rewrite output."""
    if out_text is None:
        return None, None
    struct_present = re.search(r"\bstruct\s+PSOutput\b\s*\{", out_text) is not None
    typedef_present = re.search(r"\btypedef\s+PSOutput\s+PSPointOutput\b", out_text) is not None
    return struct_present, typedef_present


def version_of(dll_path):
    exe = os.path.join(os.path.dirname(dll_path), "dxc.exe")
    if not os.path.exists(exe):
        return "<no dxc.exe next to dll>"
    p = subprocess.run([exe, "--version"], capture_output=True, text=True)
    return p.stdout.strip().splitlines()[0] if p.stdout else "<empty --version>"


def run_one(dll_path, shader_path, label):
    source_text = open(shader_path, "r", encoding="utf-8").read()
    argv = ARGV + [os.path.basename(shader_path)]
    print("== %s" % label)
    print("   dll:     %s" % triage.display_exe(dll_path))
    print("   version: %s" % version_of(dll_path))
    print("   argv:    %s" % subprocess.list2cmdline(argv))
    call_hr, status, out_text, err_text = rewrite(
        dll_path, source_text, os.path.basename(shader_path), argv)
    print("   RewriteWithOptions hr=0x%08x" % (call_hr & 0xFFFFFFFF))
    print("   GetStatus=0x%08x" % (status & 0xFFFFFFFF))
    if err_text:
        print("   errors: %s" % err_text.strip().replace("\n", " | ")[:300])
    struct_present, typedef_present = classify(out_text)
    print("   struct PSOutput{...} present=%s   typedef PSPointOutput present=%s"
          % (struct_present, typedef_present))
    print("   --- output ---")
    for line in (out_text or "").splitlines():
        print("   | %s" % line)
    print()
    return call_hr, status, struct_present, typedef_present, out_text


def write_capture(shader_path, label, expect, dll_path, call_hr, status,
                   out_text):
    """File a `variant-<label>-main-debug.txt` capture for a control/variant
    input to the rewriter, scored with the issue's own predicate.

    This is the rewriter-harness equivalent of `triage.py run --shader
    --label --expect`: `triage.py`'s own `run` drives an ordinary `dxc.exe`
    compile and cannot invoke `RewriteWithOptions` at all (see notes.md /
    method-notes.md), so this writes the same *shape* of capture -- reusing
    `triage.probe_path` for the filename and `triage.classify` (the exact
    code `reindex`/`audit` re-score with) for the verdict -- instead of
    inventing a parallel format or a parallel predicate evaluator. `match.json`
    is the right predicate here (unlike for the downstream recompile check):
    its structural regex is written against exactly this kind of rewritten-
    HLSL text, and it is what already produced every `present=`/`no-repro`/
    `repro` claim already written in notes.md for these shaders.
    """
    d = os.path.dirname(shader_path) or "."
    out_path = triage.probe_path(d, "main-debug", "match.json", label)
    text = out_text or ""
    verdict, reason = triage.classify(
        5292, text, status, False, "match.json", explain=True)
    struct_present, typedef_present = classify(out_text)
    shader_name = os.path.basename(shader_path)
    argv = ARGV + [shader_name]
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(
            "# compiler: main-debug\n"
            "# exe: %s\n"
            "# ran: %s\n"
            "# cmd: %s\n"
            "# harness: measure-rewrite.py "
            "(IDxcRewriter2::RewriteWithOptions; not a dxc.exe invocation "
            "-- see notes.md)\n"
            "# call-hr: 0x%08x\n"
            "# exit: %d\n"
            "# timed_out: 0\n"
            "# struct-present: %s\n"
            "# typedef-present: %s\n"
            "# match: match.json\n"
            "# verdict: %s\n"
            % (triage.display_exe(dll_path), triage.now(),
               subprocess.list2cmdline(argv), call_hr & 0xFFFFFFFF,
               status, struct_present, typedef_present, verdict))
        if reason:
            f.write("# invalid-probe-reason: %s\n" % reason)
        f.write("# variant: %s (%s)\n" % (label, shader_name))
        f.write("# expect: %s\n" % expect)
        f.write("\n%s" % triage.redact_paths(text))
    print("captured: %s (verdict=%s, expect=%s)" % (out_path, verdict, expect))
    if triage.expectation_violated(expect, verdict):
        print("WARNING: control expected %s but scored %s." % (expect, verdict),
              file=sys.stderr)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shader", default="repro.hlsl")
    ap.add_argument("--dll")
    ap.add_argument("--history", action="store_true")
    ap.add_argument("--label", help="name this run as a control/variant "
                                    "capture, filed as variant-<label>-"
                                    "main-debug.txt and scored against "
                                    "match.json, like triage.py run --label")
    ap.add_argument("--expect", choices=["match", "no-match"],
                    help="what this control must score; required with "
                         "--label, re-checked on every reindex")
    args = ap.parse_args()
    if bool(args.label) != bool(args.expect):
        sys.exit("--label and --expect must be given together, so the "
                 "capture always declares what it is expected to prove")
    if args.label and args.dll:
        sys.exit("refusing to file a labelled capture against a non-"
                 "ground-truth --dll; this issue's captures are all main-"
                 "debug (see notes.md)")

    if args.history:
        rows = triage.con().execute(
            "SELECT tag, build_date, cached_path FROM releases "
            "WHERE cached_path IS NOT NULL ORDER BY build_date").fetchall()
        exe = triage.resolve_compiler("main-debug")
        gt_dll = os.path.join(os.path.dirname(exe), "dxcompiler.dll")
        entries = [("main-debug", "n/a (local build)", gt_dll)]
        for tag, build_date, cached_path in rows:
            dll = os.path.join(os.path.dirname(cached_path), "dxcompiler.dll")
            entries.append((tag, build_date, dll))

        os.chdir(HERE)
        print("issue 5292 rewriter release history")
        print("primary repro: repro.hlsl, argv: %s" % subprocess.list2cmdline(
            ARGV + ["repro.hlsl"]))
        print()
        summary = []
        for tag, build_date, dll in entries:
            if not os.path.exists(dll):
                print("== %s (%s): dxcompiler.dll NOT FOUND at %s -- invalid probe"
                      % (tag, build_date, dll))
                print()
                summary.append((tag, build_date, "invalid-probe(no-dll)"))
                continue
            call_hr, status, struct_present, typedef_present, _ = run_one(
                dll, "repro.hlsl", "%s (%s)" % (tag, build_date))
            if call_hr != 0:
                verdict = "invalid-probe(call-failed)"
            elif struct_present is None:
                verdict = "invalid-probe(no-output)"
            elif (not struct_present) and typedef_present:
                verdict = "REPRO (dangling typedef)"
            elif struct_present and typedef_present:
                verdict = "no-repro (struct kept)"
            elif (not struct_present) and (not typedef_present):
                verdict = "no-repro (typedef also removed)"
            else:
                verdict = "no-repro (other)"
            summary.append((tag, build_date, verdict))

        print("summary")
        print("%-16s %-12s %s" % ("tag", "build_date", "verdict"))
        for tag, build_date, verdict in summary:
            print("%-16s %-12s %s" % (tag, build_date, verdict))
        return

    dll = args.dll
    if not dll:
        exe = triage.resolve_compiler("main-debug")
        dll = os.path.join(os.path.dirname(exe), "dxcompiler.dll")
    os.chdir(HERE)
    call_hr, status, _, _, out_text = run_one(
        dll, args.shader, "main-debug" if not args.dll else args.dll)
    if args.label:
        write_capture(args.shader, args.label, args.expect, dll, call_hr,
                      status, out_text)


if __name__ == "__main__":
    main()
