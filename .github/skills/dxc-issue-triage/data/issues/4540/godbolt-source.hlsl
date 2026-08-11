// Compiler Explorer publication source for issue 4540.
//
// CE gives every pane one shared source, so the one-variable A/B is expressed with a
// preprocessor guard: the pane compiled with -DNO_STATIC drops the `static` keyword and is
// otherwise identical. Everything else is byte-for-byte the shader from the issue body.
//
// The transformation itself is controlled locally: manual-case-godbolt-transform.txt shows
// this file with and without -DNO_STATIC producing exactly the same two globals as the
// untransformed repro.hlsl and control-no-static.hlsl.
RWBuffer<uint> TileArgsBufferOut;
RWBuffer<uint> TilesOut;

#ifdef NO_STATIC
groupshared uint storeTile;
#else
static groupshared uint storeTile;
#endif

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
