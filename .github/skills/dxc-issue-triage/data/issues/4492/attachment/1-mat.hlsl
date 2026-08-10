#pragma pack_matrix(row_major)

struct Test2_0
{
    matrix<half,int(4),int(4)>  m_0;
};


#line 103
StructuredBuffer<Test2_0 > data2_0 : register(t1);


#line 61
vector<half,2> Test2_getFloat16_2_0(Test2_0 this_0, uint i_0)
{
    switch(i_0)
    {
    case int(0):
        {

#line 65
            return vector<half,2>(this_0.m_0[int(0)][int(0)], this_0.m_0[int(0)][int(1)]);
        }
    case int(1):
        {

#line 66
            return vector<half,2>(this_0.m_0[int(0)][int(2)], this_0.m_0[int(0)][int(3)]);
        }
    case int(2):
        {

#line 67
            return vector<half,2>(this_0.m_0[int(1)][int(0)], this_0.m_0[int(1)][int(1)]);
        }
    case int(3):
        {

#line 68
            return vector<half,2>(this_0.m_0[int(1)][int(2)], this_0.m_0[int(1)][int(3)]);
        }
    case int(4):
        {

#line 69
            return vector<half,2>(this_0.m_0[int(2)][int(0)], this_0.m_0[int(2)][int(1)]);
        }
    case int(5):
        {

#line 70
            return vector<half,2>(this_0.m_0[int(2)][int(2)], this_0.m_0[int(2)][int(3)]);
        }
    case int(6):
        {

#line 71
            return vector<half,2>(this_0.m_0[int(3)][int(0)], this_0.m_0[int(3)][int(1)]);
        }
    case int(7):
        {

#line 72
            return vector<half,2>(this_0.m_0[int(3)][int(2)], this_0.m_0[int(3)][int(3)]);
        }
    }

#line 74
    return vector<half,2>(0.00000000000000000000, 0.00000000000000000000);
}


#line 100
RWStructuredBuffer<float > result_0 : register(u0);


#line 150
[shader("compute")][numthreads(1, 1, 1)]
void testStructuredBufferMatrixLoad2()
{
    int i_1;
    uint idx_0;

#line 152
    Test2_0 _S1 = data2_0[0U];



    i_1 = int(0);
    idx_0 = 0U;
    for(;;)
    {

#line 156
        if(i_1 < int(8))
        {
        }
        else
        {
            break;
        }

#line 158
        vector<half,2> v_0 = Test2_getFloat16_2_0(_S1, (uint) i_1);
        uint idx_1 = idx_0 + 1U;

#line 159
        float _S2 = (float) v_0.x;

#line 159
        result_0[idx_0] = _S2;
        uint _S3 = idx_1 + 1U;

#line 160
        float _S4 = (float) v_0.y;

#line 160
        result_0[idx_1] = _S4;

#line 156
        int _S5 = i_1 + int(1);

#line 156
        i_1 = _S5;
        idx_0 = _S3;
    }



    return;
}

