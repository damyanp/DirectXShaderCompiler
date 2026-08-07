Texture2D<float4> g_texture;

struct smallPayload
{
	Texture2D<float4> texture;
};


[numthreads(1, 1, 1)]
void main()
{
    smallPayload p;
    p.texture = g_texture;
    DispatchMesh(1, 1, 1, p);
}
