// Issue 3708, comment 1 (llvm-beanz, https://godbolt.org/z/Mjh4e1G7b) verbatim in
// content, restated with an entry point that reads the arrays so nothing is
// elided. His annotation on the original was "Only array1 and array3 compile
// without errors". Retargeted from ps_6_6 to ps_6_0 so old releases can run it.
static const uint  scalarLength  = 10;
static const uint2 vectorLengths = uint2(20, 30);

float4 main() : SV_Target
{
    int array1[10];                 // plain literal
    int array2[(10).x];             // swizzle of a literal      <- issue body
    int array3[scalarLength];       // static const scalar
    int array4[scalarLength.x];     // swizzle of a const SCALAR
    int array5[vectorLengths.x];    // swizzle of a const vector
    int array6[vectorLengths[1]];   // subscript of a const vector
    array1[0] = 1; array2[0] = 2; array3[0] = 3;
    array4[0] = 4; array5[0] = 5; array6[0] = 6;
    return array1[0] + array2[0] + array3[0]
         + array4[0] + array5[0] + array6[0];
}
