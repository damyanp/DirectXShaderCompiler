#pragma pack_matrix(row_major)

// Negative control for #4492's predicate.
//
// Same shape as repro.hlsl -- same entry point name, same profile, same flags, a
// StructuredBuffer whose $Element is also 32 bytes, and the same
// @dx.op.rawBufferLoad.f16 instrument -- but the half4x4 is replaced by an array of
// half4 vectors. The scalar stride there is not the code path under test.
//
// The predicate MUST NOT match this: if it does, it is matching structurally normal
// f16 structured-buffer IR rather than the doubled-stride defect.

struct Test2_0
{
    vector<half,4>  m_0[int(4)];
};


StructuredBuffer<Test2_0 > data2_0 : register(t1);


vector<half,2> Test2_getFloat16_2_0(Test2_0 this_0, uint i_0)
{
    switch(i_0)
    {
    case int(0):
        {
            return vector<half,2>(this_0.m_0[int(0)][int(0)], this_0.m_0[int(0)][int(1)]);
        }
    case int(1):
        {
            return vector<half,2>(this_0.m_0[int(0)][int(2)], this_0.m_0[int(0)][int(3)]);
        }
    case int(2):
        {
            return vector<half,2>(this_0.m_0[int(1)][int(0)], this_0.m_0[int(1)][int(1)]);
        }
    case int(3):
        {
            return vector<half,2>(this_0.m_0[int(1)][int(2)], this_0.m_0[int(1)][int(3)]);
        }
    case int(4):
        {
            return vector<half,2>(this_0.m_0[int(2)][int(0)], this_0.m_0[int(2)][int(1)]);
        }
    case int(5):
        {
            return vector<half,2>(this_0.m_0[int(2)][int(2)], this_0.m_0[int(2)][int(3)]);
        }
    case int(6):
        {
            return vector<half,2>(this_0.m_0[int(3)][int(0)], this_0.m_0[int(3)][int(1)]);
        }
    case int(7):
        {
            return vector<half,2>(this_0.m_0[int(3)][int(2)], this_0.m_0[int(3)][int(3)]);
        }
    }

    return vector<half,2>(0.00000000000000000000, 0.00000000000000000000);
}


RWStructuredBuffer<float > result_0 : register(u0);


[shader("compute")][numthreads(1, 1, 1)]
void testStructuredBufferMatrixLoad2()
{
    int i_1;
    uint idx_0;

    Test2_0 _S1 = data2_0[0U];

    i_1 = int(0);
    idx_0 = 0U;
    for(;;)
    {
        if(i_1 < int(8))
        {
        }
        else
        {
            break;
        }

        vector<half,2> v_0 = Test2_getFloat16_2_0(_S1, (uint) i_1);
        uint idx_1 = idx_0 + 1U;

        float _S2 = (float) v_0.x;

        result_0[idx_0] = _S2;
        uint _S3 = idx_1 + 1U;

        float _S4 = (float) v_0.y;

        result_0[idx_1] = _S4;

        int _S5 = i_1 + int(1);

        i_1 = _S5;
        idx_0 = _S3;
    }

    return;
}
