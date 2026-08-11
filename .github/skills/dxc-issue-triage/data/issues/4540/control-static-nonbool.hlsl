// Diagnostic variant for issue 4540, not a control of the primary predicate.
// Same as repro.hlsl but the stored values are 0 and 2 rather than 0 and 1. The reporter
// described the trigger as "bool-like" variables; this asks whether the narrowing follows
// the value range or the `static` keyword.
RWBuffer<uint> TileArgsBufferOut;
RWBuffer<uint> TilesOut;

static groupshared uint storeTile;

[numthreads(8,8,1)]
void main(uint3 dtid : SV_DispatchThreadID, uint3 gtid : SV_GroupThreadID, uint3 gid : SV_GroupID)
{
	if (gtid.x == 0 && gtid.y == 0)
	{
		storeTile = 0;
	}
	
	GroupMemoryBarrierWithGroupSync();

	storeTile = 2;

	GroupMemoryBarrierWithGroupSync();

	if (gtid.x == 0 && gtid.y == 0 && storeTile > 0)
	{
		const uint tileId = gid.y * 1024 + gid.x;

		uint tileStoreIdx;
		InterlockedAdd(TileArgsBufferOut[0], 1, tileStoreIdx);
		TilesOut[tileStoreIdx] = tileId;			
	}
}
