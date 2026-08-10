struct ParamUnused {
	uint A;
};

struct ParamUsed {
	uint B;
};

uint Helper(ParamUnused notRead, ParamUsed isRead)
{
	return isRead.B;
}

RWStructuredBuffer<uint> OutBuffer;

[numthreads(1, 1, 1)]
void InitArgs()
{
	OutBuffer[0] = Helper((ParamUnused)0, (ParamUsed)0);
}
