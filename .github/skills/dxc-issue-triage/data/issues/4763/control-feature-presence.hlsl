// FEATURE-PRESENCE CONTROL for issue 4763.
//
// The smallest shader that uses the construct under test at all: one resource
// declared inside a legacy cbuffer block, read by the entry point. Run on every
// release probed, under the repro's own profile and flags.
//
//   compiles cleanly  -> that release can express "a resource inside a cbuffer",
//                        so a result on repro.hlsl from that release is real.
//   rejected          -> that release cannot express the construct, and its
//                        repro.hlsl result measured nothing.
cbuffer CB
{
    Buffer<float4> bufferData;
    uint myInt;
};
float4 PSMain() : SV_Target0
{
    return bufferData[0] * myInt;
}
