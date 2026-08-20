// Control: pre-decrement with no intervening inout call at all.
// Expected: a single "-1" constant, proving the baseline pre-decrement lowering
// is correct and that "-1" is an anchor the reader can actually see.
uint PSMain(uint i : I) : SV_TARGET
{
    --i;
    return i;
}
