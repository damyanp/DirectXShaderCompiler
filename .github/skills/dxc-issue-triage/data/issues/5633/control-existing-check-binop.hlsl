// Existing-diagnostic control (D): the out-of-bounds element is used inside
// an ordinary binary operation (`+ 0.0`) rather than a swizzle or member
// access. This is the negative control for control-existing-check-swizzle
// and control-existing-check-member: it shows that wrapping the subscript in
// *some* further expression is not, by itself, what silences the check --
// only a swizzle or a struct/buffer member base does.
float4 main() : SV_TARGET
{
    float arr[1];
    float y = arr[2000] + 0.0;
    return y.xxxx;
}
