// NEGATIVE CONTROL for issue 4629 -- "an ordinary diagnosed error is not a crash".
//
// This is the control that resolves the central hazard of this issue. On Windows
// dxc returns E_FAIL (0x80004005) for ordinary diagnosed errors, and E_FAIL is
// ALSO the status the DXC_E_LLVM_CAST_ERROR path surfaces as. So exit status
// alone cannot separate "the compiler crashed internally" from "the compiler
// correctly told the user their code is wrong".
//
// `nosuchtype` is undeclared, so this exits 0x80004005 with an `error:` line and
// no internal-failure marker. Expected: no-match. If internal_failure fired here
// it would be inventing bugs out of every failed compile, which is the more
// dangerous direction of error.

struct PSInput
{
};

float4 PSMain( PSInput input ) : SV_TARGET
{
    nosuchtype obj ;
    return float4 ( obj . albedo , 1 ) ;
} 
