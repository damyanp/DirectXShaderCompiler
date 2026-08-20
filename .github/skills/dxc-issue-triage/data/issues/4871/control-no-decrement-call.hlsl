void Func(inout uint byteOffset)
{
}

// Control: call the inout function with a plain, undecremented argument.
// No decrement appears anywhere in source. Expected: no "-1"/"-2" arithmetic
// constant produced at all -- proves the inout copy-in/copy-out machinery by
// itself does not fabricate a spurious subtraction; the defect needs the
// combination of "--i" written directly as the call argument.
uint PSMain(uint i : I) : SV_TARGET
{
    Func(i);
    return i;
}
