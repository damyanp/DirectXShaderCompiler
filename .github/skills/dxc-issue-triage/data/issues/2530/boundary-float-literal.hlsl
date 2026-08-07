// #2530 boundary probe: the same float->uint conversion, but applied to a
// floating *literal* rather than to a `static const float` variable.
// clang's C++03 ICE rules special-case a cast whose operand is a FloatingLiteral
// (tools/clang/lib/AST/ExprConstant.cpp, CheckICE, ImplicitCast/CStyleCast/
// CXXFunctionalCast case), so this one is an integer constant expression and
// must compile. Expect no-match.
float4 main() : SV_Target
{
    float array[uint(1.0f)] = { 1.0f };
    return (float4)0;
}
