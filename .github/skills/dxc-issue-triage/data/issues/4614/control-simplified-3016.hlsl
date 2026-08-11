// The test added by 527d58e5a (PR #3827), the commit that closed #3016.
// Source copied verbatim from
// tools/clang/test/HLSLFileCheck/hlsl/types/struct/embeddedEmptyStruct.hlsl,
// minus its RUN: line. This is the "simplified version" pow2clk refers to in
// https://github.com/microsoft/DirectXShaderCompiler/issues/3016 :
// "I guess that's what I get for including my simplified version instead of
// the original repro in the test suite."
// It has no base-class inheritance and no assignment of an empty struct.

struct s0 {};
struct s1 { s0 a; uint b; };

s1 main() : OUT { s1 s; return s; }
