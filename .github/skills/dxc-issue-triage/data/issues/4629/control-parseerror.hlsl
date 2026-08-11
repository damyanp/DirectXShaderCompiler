// NEGATIVE CONTROL for issue 4629 -- the diagnosed-error / internal-failure line.
//
// This is the control that resolves the central hazard of this issue. On Windows
// dxc returns E_FAIL (0x80004005) for ordinary diagnosed errors, and E_FAIL is
// ALSO the status that the DXC_E_LLVM_CAST_ERROR path -- the one the reporter
// saw -- surfaces as. So exit status alone cannot separate "the compiler failed
// internally" from "the compiler correctly told the user their code is wrong".
//
// The `return` statement below is missing its semicolon: a plain parse error, on
// present-day code, that trips none of the classifier's feature-absence markers.
// Expected: no-match, at exit 0x80004005. If internal_failure fired here it
// would invent a crash out of every failed compile, which is the more dangerous
// direction of error.
//
// (control-syntaxerror.hlsl makes the same measurement with an undeclared type
// and is scored invalid-probe instead, because "unknown type name" is one of the
// feature-absence markers. Both exit 0x80004005; neither scores repro.)

struct PSInput
{
};

float4 PSMain( PSInput input ) : SV_TARGET
{
    return float4 ( 1 , 1 , 1 , 1 )
} 
