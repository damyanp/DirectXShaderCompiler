float2x2 mymatrix;
RWBuffer<float> Output; 

main()
{ 
  Output[0] = float2(1,2) * mymatrix;
}
