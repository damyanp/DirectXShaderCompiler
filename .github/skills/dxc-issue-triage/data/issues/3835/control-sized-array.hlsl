// Discriminating control for #3835: byte-for-byte repro.hlsl except that the
// two array-assignment initialisers name a COMPLETE array type --
//   float _expr13[1] = ...   instead of   float _expr13[] = ...
// Everything else the thread calls invalid about the shader is untouched:
// perVertexStruct's gl_PointSize / gl_ClipDistance / gl_CullDistance are still
// read while uninitialised. Must score no-match, which is what shows the
// symptom is the incomplete array type and not the shader's other invalidity.
struct gl_PerVertex {
    float4 gl_Position : SV_Position;
    float gl_PointSize : PSIZE;
    float gl_ClipDistance[1] : SV_ClipDistance;
    float gl_CullDistance[1] : SV_CullDistance;
};

struct type10 {
    float2 member : LOC0;
    float4 gl_Position1 : SV_Position;
    float gl_PointSize1 : PSIZE;
    float gl_ClipDistance1[1] : SV_ClipDistance;
    float gl_CullDistance1[1] : SV_CullDistance;
};

static float2 v_uv;
static float2 a_uv;
static gl_PerVertex perVertexStruct;
static float2 a_pos;

struct VertexInput {
    float2 a_uv2 : LOC1;
    float2 a_pos2 : LOC0;
};

void main()
{
    float2 _expr12 = a_uv;
    v_uv = _expr12;
    float2 _expr13 = a_pos;
    perVertexStruct.gl_Position = float4(_expr13.x, _expr13.y, 0.0, 1.0);
    return;
}

type10 vert_main(VertexInput vertexinput)
{
    a_uv = vertexinput.a_uv2;
    a_pos = vertexinput.a_pos2;
    main();
    float2 _expr10 = v_uv;
    float4 _expr11 = perVertexStruct.gl_Position;
    float _expr12 = perVertexStruct.gl_PointSize;
    float _expr13[1] = perVertexStruct.gl_ClipDistance;
    float _expr14[1] = perVertexStruct.gl_CullDistance;
    const type10 type10_ = { _expr10, _expr11, _expr12, _expr13, _expr14 };
    return type10_;
}
