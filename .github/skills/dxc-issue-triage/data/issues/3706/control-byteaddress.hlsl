// Negative control for #3706: fully correct code that nevertheless emits an `undef`
// operand inside the very op the issue is about.
//
// For a ByteAddressBuffer (DXIL ResourceKind::RawBuffer) the *elementOffset* operand of
// dx.op.rawBufferLoad is REQUIRED to be undef -- lib/DxilValidation/DxilValidation.cpp
// errors with InstrCoordinateCountForRawTypedBuf if it is anything else. A predicate that
// looked for "undef anywhere in a rawBufferLoad" would score this correct shader as a
// reproduction. This is #3009's trap, on this issue's own op.
ByteAddressBuffer babuf;

uint main(uint i : IN) : OUT
{
     return babuf.Load(i * 4);
}
