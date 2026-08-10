// Negative control for #3835: the same shader shape as repro.hlsl -- the same
// gl_PerVertex / type10 structs, the same SV_ClipDistance[1] and
// SV_CullDistance[1] arrays, the same vert_main entry -- but with every field
// initialised and NO array-assignment initialisation of an incomplete array
// type. Run with repro.hlsl's exact arguments; must score no-match, proving
// the internal_failure predicate does not fire on a clean compile of this
// shader family.
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

struct VertexInput {
    float2 a_uv2 : LOC1;
    float2 a_pos2 : LOC0;
};

type10 vert_main(VertexInput vertexinput)
{
    gl_PerVertex perVertexStruct;
    perVertexStruct.gl_Position = float4(vertexinput.a_pos2.x, vertexinput.a_pos2.y, 0.0, 1.0);
    perVertexStruct.gl_PointSize = 1.0;
    perVertexStruct.gl_ClipDistance[0] = 0.0;
    perVertexStruct.gl_CullDistance[0] = 0.0;

    type10 type10_;
    type10_.member = vertexinput.a_uv2;
    type10_.gl_Position1 = perVertexStruct.gl_Position;
    type10_.gl_PointSize1 = perVertexStruct.gl_PointSize;
    type10_.gl_ClipDistance1[0] = perVertexStruct.gl_ClipDistance[0];
    type10_.gl_CullDistance1[0] = perVertexStruct.gl_CullDistance[0];
    return type10_;
}
