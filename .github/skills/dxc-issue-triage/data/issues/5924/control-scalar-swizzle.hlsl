// Control: plain top-level scalar swizzle, no struct/template involved at
// all. Proves the defect is not "swizzle on a scalar" in general -- only a
// swizzle whose base's *static* type is a template type parameter that
// resolves to a scalar. Expected: compiles clean, no "member reference base
// type ... is not a structure or union" diagnostic.
float2 PSMain(float t : A) : SV_TARGET0
{
    return t.xx;
}
