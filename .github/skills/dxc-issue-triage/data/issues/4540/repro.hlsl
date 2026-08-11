// Verbatim from issue 4540's body (microsoft/DirectXShaderCompiler#4540).
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

	storeTile = 1;

	GroupMemoryBarrierWithGroupSync();

	if (gtid.x == 0 && gtid.y == 0 && storeTile > 0)
	{
		const uint tileId = gid.y * 1024 + gid.x;

		uint tileStoreIdx;
		InterlockedAdd(TileArgsBufferOut[0], 1, tileStoreIdx);
		TilesOut[tileStoreIdx] = tileId;			
	}
}
