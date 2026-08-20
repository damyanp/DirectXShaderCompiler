// Self-test control for match.json's "not_regex warning|error" clause. This
// has nothing to do with issue #5633's out-of-bounds question -- it is an
// unrelated implicit-conversion truncation warning, used only to prove the
// predicate's absence clause is actually capable of detecting a "warning"
// token in this compiler's -spirv output. Without this, a compiler build that
// happens to be silent for any reason (not just the reported one) would
// satisfy the predicate vacuously and its "no diagnostic" result would be
// unfalsifiable.
float4 main() : SV_TARGET
{
    float x;
    int y = 3.9;
    return x.xxxx;
}
