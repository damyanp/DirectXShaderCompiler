// Validator control for issue 4540. This exceeds the 32KB groupshared budget, so DXIL
// validation must REJECT it (ValidationRule::SmMaxTGSMSizeOnEntry). It exists to prove that
// the validator's groupshared rules actually run on a module of this shape -- without it,
// "the validator accepts the i1 groupshared global" is indistinguishable from "the validator
// was never asked".
RWBuffer<uint> TilesOut;

groupshared uint big[16384];   // 65536 bytes, over the 32768-byte limit

[numthreads(8,8,1)]
void main(uint3 gtid : SV_GroupThreadID)
{
	big[gtid.x] = gtid.y;
	GroupMemoryBarrierWithGroupSync();
	TilesOut[gtid.x] = big[gtid.y];
}
