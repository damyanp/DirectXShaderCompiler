// Value-corruption probe for issue 4540. Not a control of the primary predicate.
// The variable is written with 2 and then read back into the output buffer. If the i1
// storage type is only a spelling difference, the buffer receives 2. If the narrowing is
// lossy, it receives 1.
RWBuffer<uint> TilesOut;

static groupshared uint storeTile;

[numthreads(8,8,1)]
void main(uint3 gtid : SV_GroupThreadID, uint3 gid : SV_GroupID)
{
	if (gtid.x == 0 && gtid.y == 0)
	{
		storeTile = 2;
	}

	GroupMemoryBarrierWithGroupSync();

	TilesOut[gtid.x] = storeTile;
}
