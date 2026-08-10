// compile with :
// dxc.exe main.hlsl /Zi /E"main" /Od /Fo test.mso /Tms_6_6 -Qembed_debug

struct Vertex {
	float4 m_sv_position : SV_POSITION;
	float m_value : VALUE;
};

void setVertex( out Vertex dst, float src ) { dst.m_sv_position = 0; dst.m_value = src; }

[numthreads(128, 1, 1)]
[OutputTopology("triangle")]
void main( out vertices Vertex _vertices[ 64 ] 
	, out indices uint3 _triangles[ 126 ]
	, in uint3 _sv_groupthreadid : SV_GROUPTHREADID )
{
	const float toto = -1.0;

	SetMeshOutputCounts( 64, 126 );

	if ( _sv_groupthreadid.x < 64 ) {
		_vertices[ _sv_groupthreadid.x ].m_sv_position = float4( 0.0, 0.0, 0.0, 0.0 );
		_vertices[ _sv_groupthreadid.x ].m_value = 0;
		setVertex( _vertices[ _sv_groupthreadid.x ], sign( toto ) );
	}


	if ( _sv_groupthreadid.x < 126 )
	{
		_triangles[ _sv_groupthreadid.x ] = uint3( 1, 2, 3 );
	}
}
