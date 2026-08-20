void Func(inout uint byteOffset)
{
}

uint PSMain(uint i : I) : SV_TARGET
{
    Func(--i);  // Subtracts 2...
    return i;
}
