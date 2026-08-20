Reported symptom (from issue text and the linked Compiler Explorer example,
https://godbolt.org/z/9PfEPYa3M, retrieved via the shortlinkinfo API):

DXC emits `-Wliteral-conversion` warnings for out-of-range float/double-to-int/uint literal
conversions of the form:

    warning: implicit conversion from 'literal float' to 'int' changes value from <FROM> to <TO>

The reporter says the printed `<TO>` value is sometimes wrong -- it does not match the value
the conversion will actually produce (the value described in the source comment on each line,
matching what an actual int/uint clamp of the double would produce). Concretely, for
`to_int(-2147483648.0)` the warning claims the value changes to `2147483647` (INT_MAX), but the
comment (and correct clamped conversion) says the result is `-2147483648` (INT_MIN) -- the sign
is wrong. The issue also says Clang 3.8 has this same wrong behavior and Clang 3.9 fixed it, and
that a later Clang version stopped printing a specific `<TO>` value at all for undefined
out-of-range conversions (printing "is undefined" instead), because these conversions are UB.

This reproduces if:
  - dxc still emits a `<TO>` value in the `-Wliteral-conversion` warning that mismatches the
    value obtained by actually clamping the source double to the destination integer type's
    range (matching the sign-correct clamp shown in each line's comment), OR
  - more generally, the wrong printed value class of bug described in the issue (3.8-style
    clamping of the two's-complement pattern via the wrong sign, not via range-clamping) is
    still present.

This does NOT reproduce (verdict does-not-repro / changed-behavior) if dxc's `<TO>` values now
match the correct clamp for every case in the repro, or if dxc has moved to the "is undefined"
wording documented in the issue as the target end-state, since in that case there is no
`<TO>` value left to be wrong.

Repro quality: complete -- the exact HLSL source is recovered verbatim from the issue's
Compiler Explorer link via `GET https://godbolt.org/api/shortlinkinfo/9PfEPYa3M`, and the exact
warning text quoted in the issue body was produced by that exact source compiled with
`-T cs_6_6` (CE's dxc_trunk default for this shortlink).
