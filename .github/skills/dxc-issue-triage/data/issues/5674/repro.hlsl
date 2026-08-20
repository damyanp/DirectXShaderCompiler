float2x2 matrix;
RWBuffer<float> Output; 

main()
{ 
  Output[0] = float2(1,2) * matrix;
}
