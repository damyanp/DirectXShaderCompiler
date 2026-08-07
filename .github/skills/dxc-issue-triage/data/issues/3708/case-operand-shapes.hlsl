// Which operand shapes are refused, beyond the two the issue names.
// Matrices and rvalues are covered here, as is the obvious workaround of
// folding the component into a `static const` scalar first.
static const uint    s   = 10;
static const uint2   v2  = uint2(20, 30);
static const uint2x2 m22 = uint2x2(1, 2, 3, 4);
static const uint    via = v2.x;        // the "fold it first" workaround

float4 main() : SV_Target
{
    int a01[uint2(20, 30).x];    // rvalue vector, swizzle
    int a02[uint2(20, 30)[0]];   // rvalue vector, subscript
    int a03[v2.r];               // colour-channel spelling of .x
    int a04[m22._11];            // matrix, one-based named component
    int a05[m22._m00];           // matrix, zero-based named component
    int a06[m22[0][0]];          // matrix, double subscript
    int a07[(10).xx[0]];         // multi-component swizzle, then subscript
    int a08[v2.x + v2.y];        // arithmetic over two swizzles
    int a09[via];                // static const folded from a swizzle
    a01[0]=1; a02[0]=1; a03[0]=1; a04[0]=1; a05[0]=1;
    a06[0]=1; a07[0]=1; a08[0]=1; a09[0]=1;
    return a01[0] + a02[0] + a03[0] + a04[0] + a05[0]
         + a06[0] + a07[0] + a08[0] + a09[0];
}
