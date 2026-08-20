void Func(inout uint byteOffset)
{
}

// Control: decrement in its own statement, THEN pass the already-decremented
// value to the inout function. Isolates whether the double-subtraction needs
// the decrement to be written as the call argument expression itself, or
// happens whenever Func() is called at all.
// Expected: a single "-1" constant (same as the plain-decrement control).
uint PSMain(uint i : I) : SV_TARGET
{
    --i;
    Func(i);
    return i;
}
