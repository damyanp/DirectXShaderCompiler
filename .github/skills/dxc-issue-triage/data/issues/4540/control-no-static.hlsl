// Control for issue 4540: byte-for-byte the issue's shader with `static` removed from the
// groupshared declaration. The issue itself names this as the configuration that behaves
// correctly ("This bug does not reproduce when omitting \"static\""), so the symptom
// predicate must NOT match here. It differs from repro.hlsl in exactly one token.
RWBuffer<uint> TileArgsBufferOut;
RWBuffer<uint> TilesOut;

groupshared uint storeTile;

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
