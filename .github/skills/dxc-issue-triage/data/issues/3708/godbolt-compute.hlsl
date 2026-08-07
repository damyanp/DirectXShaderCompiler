// Compute restating of the repro, for Compiler Explorer. Compute is the one
// stage all three compilers in the link can handle: clang's DXIL backend
// cannot lower a pixel shader writing SV_Target, and FXC needs a 5_x profile.
// `okLiteral` is the pane's own control -- every compiler must accept it, so a
// pane that rejects only the swizzled bounds has rejected them for the reason
// under test and not because of the stage, the profile or the buffer.
static const uint2 vectorLengths = uint2(20, 30);

RWBuffer<uint> Out;

[numthreads(1, 1, 1)]
void main(uint3 tid : SV_DispatchThreadID)
{
    int okLiteral[10];                  // control: accepted everywhere
    int swizzleLiteral[(10).x];         // the issue body's minimal case
    int swizzleVector[vectorLengths.x];
    int indexVector[vectorLengths[1]];
    okLiteral[0] = 1; swizzleLiteral[0] = 2;
    swizzleVector[0] = 3; indexVector[0] = 4;
    Out[tid.x] = okLiteral[0] + swizzleLiteral[0]
               + swizzleVector[0] + indexVector[0];
}
