Texture2D<float4> g_texture;

struct smallPayload
{
	uint value;
};


[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    p.value = 1;
    DispatchMesh(1, 1, 1, p);
}
