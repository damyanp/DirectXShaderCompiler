"""Derive #4307's controls and extra cases from repro.hlsl.

Run from anywhere:  python make-variants.py   (after make-repro.py)

Deriving these mechanically rather than typing them keeps the promise that a
control differs from the repro in exactly one way, and -- for the line-count-
preserving control -- keeps every diagnostic's `Line:`/`:NN:` number comparable
between the two captures. The script asserts both properties and fails loudly
rather than writing a control that quietly measures something else.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPRO = HERE / "repro.hlsl"

# Line 22 of the reporter's shader is the whole subject of the issue: it *reads*
# the mesh output member before writing it back.
READ_MODIFY_WRITE = "\t\t_vertices[ _sv_groupthreadid.x ].m_value *= sign( toto );"


def derive(*pairs: tuple) -> str:
    """Apply (old, new) replacements, failing loudly if an anchor is missing.

    A `str.replace` whose pattern does not match is a silent no-op, which is how
    a "variant" ends up being the repro with a bit missing -- or, worse, a shader
    that no longer compiles for a reason unrelated to the issue.
    """
    text = REPRO.read_text(encoding="utf-8")
    for old, new in pairs:
        if old not in text:
            sys.exit(f"anchor not found, refusing to write a bogus variant: {old!r}")
        text = text.replace(old, new)
    return text


def write(name: str, text: str, *, same_line_count: bool) -> None:
    original = REPRO.read_text(encoding="utf-8")
    if same_line_count:
        a, b = original.count("\n"), text.count("\n")
        if a != b:
            sys.exit(f"{name}: line count {b} != repro's {a}")
    if text == original:
        sys.exit(f"{name}: identical to repro.hlsl -- an anchor failed to match")
    (HERE / name).write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {name}  ({text.count(chr(10))} lines)")


def main() -> int:
    original = REPRO.read_text(encoding="utf-8")
    if READ_MODIFY_WRITE not in original:
        sys.exit("repro.hlsl does not contain the expected line 22; re-run make-repro.py")

    # NEGATIVE CONTROL. Identical to the repro except that the output member is
    # only ever stored to, never loaded. If the predicate still fires here it is
    # keyed to mesh shaders / /Od / entry parameters rather than to the read-back.
    write(
        "control-no-readback.hlsl",
        derive(
            (
                READ_MODIFY_WRITE,
                "\t\t_vertices[ _sv_groupthreadid.x ].m_value = sign( toto );",
            ),
        ),
        same_line_count=True,
    )

    # The issue's third ask, verbatim from the body: "The same kind of error
    # happen when you use for instance _vertices[...].m_value as a function
    # parameter even if the parameter of the function is marked as out."
    # Passing an lvalue to an `out` parameter is a copy-out in HLSL, so this is
    # a store with no read in the source -- which is exactly why the reporter
    # found the resulting error surprising.
    write(
        "case-out-param.hlsl",
        derive(
            (
                "struct Vertex {",
                "void setValue( out float dst, float src ) { dst = src; }\n\nstruct Vertex {",
            ),
            (
                READ_MODIFY_WRITE,
                "\t\tsetValue( _vertices[ _sv_groupthreadid.x ].m_value, sign( toto ) );",
            ),
        ),
        same_line_count=False,
    )

    # Companion to the above. `inout` copies in as well as out, so this is the
    # same read-modify-write as the repro's line 22, just spelled through a call.
    # It separates "any use as a function argument" from "a use that reads".
    write(
        "case-inout-param.hlsl",
        derive(
            (
                "struct Vertex {",
                "void scaleValue( inout float v, float s ) { v *= s; }\n\nstruct Vertex {",
            ),
            (
                READ_MODIFY_WRITE,
                "\t\tscaleValue( _vertices[ _sv_groupthreadid.x ].m_value, sign( toto ) );",
            ),
        ),
        same_line_count=False,
    )

    # Disambiguates the third ask. `case-out-param.hlsl` reads the body's wording
    # literally -- the *member* is the argument. The body is also compatible with
    # passing the whole element, which is a different expression shape (the
    # subscript itself, not a MemberExpr) and could plausibly diagnose
    # differently. Testing both is the difference between "the third ask does not
    # reproduce" and "the third ask does not reproduce in the shape I happened to
    # pick".
    write(
        "case-out-param-elem.hlsl",
        derive(
            (
                "\tfloat m_value : VALUE;\n};",
                "\tfloat m_value : VALUE;\n};\n\n"
                "void setVertex( out Vertex dst, float src )"
                " { dst.m_sv_position = 0; dst.m_value = src; }",
            ),
            (
                READ_MODIFY_WRITE,
                "\t\tsetVertex( _vertices[ _sv_groupthreadid.x ], sign( toto ) );",
            ),
        ),
        same_line_count=False,
    )

    # POSITIVE CONTROL for the "missing diagnostic" half of the issue. DXC does
    # have a Sema diagnostic for reading a mesh output array
    # (err_hlsl_load_from_mesh_out_arrays, tools/clang/lib/Sema/SemaExpr.cpp:698),
    # but it is guarded by `isa<ArraySubscriptExpr>(E)`, so it only fires when the
    # subscript itself is the value being read. This reads the whole element
    # instead of one member, which is precisely that shape -- so it must produce
    # the good diagnostic where the repro produces none.
    write(
        "case-elem-read.hlsl",
        derive(
            (
                READ_MODIFY_WRITE,
                "\t\tVertex _copy = _vertices[ _sv_groupthreadid.x ]; "
                "_vertices[ 0 ].m_value = _copy.m_value * sign( toto );",
            ),
        ),
        same_line_count=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
