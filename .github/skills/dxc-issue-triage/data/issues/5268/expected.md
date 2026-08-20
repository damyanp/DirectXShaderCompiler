# Expected symptom

From the issue body (verbatim repro, run as `dxr test.hlsl -E VSMain -remove-unused-globals`):

```hlsl
static const float POINT_SIZE = 3.0f;
static const float3 POINT_SIZE_3 = float3(1.0f, 1.0f, 1.0f) * POINT_SIZE;

struct PSInput
{
    float4 position : POSITION;
};

PSInput VSMain(float3 position : POSITION)
{
    PSInput psInput;
    psInput.position = float4(position, 1.0f);
    psInput.position.xyz *= POINT_SIZE_3;
    return psInput;
}
```

Claim: the entry point `VSMain` uses the static global `POINT_SIZE_3`, so the
`-remove-unused-globals` rewriter pass correctly keeps it. But `POINT_SIZE_3`'s own
initializer references another static global, `POINT_SIZE`. The rewriter does not see that
transitive reference and removes `POINT_SIZE` anyway, leaving `POINT_SIZE_3`'s initializer
referring to an identifier that no longer exists in the rewritten source. The rewritten
output should therefore fail to recompile (an undeclared-identifier error on `POINT_SIZE`
inside the surviving `POINT_SIZE_3` declaration), even though the input was valid.

"Reproduces" means: running `dxr -E VSMain -remove-unused-globals` on this source produces
rewritten HLSL that (a) omits the `POINT_SIZE` declaration, (b) keeps the `POINT_SIZE_3`
declaration whose initializer still references `POINT_SIZE`, and (c) that rewritten output
fails to compile with an undeclared-identifier (or equivalent) error when fed back through
`dxc`.

"Does not reproduce" means either `POINT_SIZE` is also kept (rewriter now understands the
transitive reference), or `POINT_SIZE_3` is also removed (rewriter no longer considers it used
some other way), or the rewritten output still compiles cleanly for some other reason.

Repro quality: **complete** — the issue body contains the exact source and exact command line;
nothing needs to be constructed.
