// Integral-constant-expression contexts that are NOT an array bound. If the
// issue title ("not considered a constant expression") is right, these must
// fail too -- but with their own diagnostics, never `variable length arrays`.
// This file is therefore the predicate's discriminating control: it is run
// with --expect no-match, which asserts that match.json names the VLA
// diagnostic and not merely "the compile failed".
static const uint2 v2 = uint2(3, 4);

enum E { A = v2.x };

float4 main(uint i : I) : SV_Target
{
    float r = 0;
    switch (i) {
        case v2.x: r = 1; break;      // case label
        case 99:   r = 2; break;
    }
    vector<float, v2.y> vv = 0;       // non-type template argument
    return r + vv.x + A;
}
