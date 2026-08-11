// Control for issue 4540. A genuinely bool-typed groupshared variable WITHOUT `static`.
// If the i1 groupshared global were merely "the variable only ever holds 0 or 1", this
// shader would produce it too. Expected: no-match (an i32 groupshared global), which
// isolates `static` -- i.e. internal linkage -- as the trigger rather than the value range.
RWBuffer<uint> TileArgsBufferOut;
RWBuffer<uint> TilesOut;

groupshared bool storeTile;

[numthreads(8,8,1)]
void main(uint3 dtid : SV_DispatchThreadID, uint3 gtid : SV_GroupThreadID, uint3 gid : SV_GroupID)
{
	if (gtid.x == 0 && gtid.y == 0)
	{
		storeTile = false;
	}
	
	GroupMemoryBarrierWithGroupSync();

	storeTile = true;

	GroupMemoryBarrierWithGroupSync();

	if (gtid.x == 0 && gtid.y == 0 && storeTile)
	{
		const uint tileId = gid.y * 1024 + gid.x;

		uint tileStoreIdx;
		InterlockedAdd(TileArgsBufferOut[0], 1, tileStoreIdx);
		TilesOut[tileStoreIdx] = tileId;			
	}
}
