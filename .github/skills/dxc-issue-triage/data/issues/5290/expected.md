# Expected symptom -- #5290

Issue title: "Rewriter: entrypoint function's param referenced types are removed
when param is not used." Tool: `dxr.exe -remove-unused-functions
-remove-unused-globals -E ps_main` (the standalone HLSL rewriter, driven
through `IDxcRewriter2`; `dxc.exe` does not expose this surface -- see #5255,
same batch, which independently establishes this).

The issue body decomposes into **two distinct asks**, per the "decompose
multi-ask issues" rule:

## Ask 1 (titled symptom): entry-point parameter type dropped

Repro: a pixel shader `ps_main(VS_OUTPUT input) : SV_Target0` whose body never
reads `input` at all. Rewriting with `-remove-unused-functions
-remove-unused-globals -E ps_main` should retain `struct VS_OUTPUT { ... };`
because it is still the type of `ps_main`'s own parameter (removing it leaves
the parameter's type undeclared, which will fail to recompile). The issue's
quoted output is missing the struct declaration entirely -- **this is the
symptom**: reproducing means the rewritten output declares `ps_main` with a
parameter of type `VS_OUTPUT` while nowhere declaring `struct VS_OUTPUT`.

A top-level comment (Snowapril, 2023-06-14) reports hitting the identical
problem and describes a fix approach ("iterating entryFnDecl->params and
remove param type from collected 'unusedTypes'"); the reporter replies "I have
already fix this" -- read as a local/private patch, not a claim that upstream
already contains a fix, since no PR from either account is linked and the
issue remains open. Ground truth is measured directly rather than assumed
either way.

## Ask 2 (second comment): nested struct type dropped via a local-variable cast

Repro: a more elaborate shader where the entry point's own parameter type
(`VS_OUTPUT`) also goes unused, but additionally declares a local variable
`Material mtl = (Material)0;` inside the function body. `Material` has a field
`LayerColor colors[4]` (an array-of-struct member). The reporter states
`struct Material` is removed from the rewritten output. Reproducing means the
rewritten output keeps `mtl`'s cast/declaration (`(Material)0`) or otherwise
still names the type `Material`, while `struct Material { ... };` (and/or its
nested `struct LayerColor { ... };`) is missing from the emitted declarations
-- again something that will not recompile.

## Repro quality

`complete` for both asks: the issue body gives runnable HLSL for each and
states the exact tool invocation; the second ask's shader is quoted verbatim
in a comment, including the intermediate `VS_APPEND`/`LayerColor` types.

## Status vocabulary

`repros` if a rewritten declaration is missing while the type is still named
by the retained function; `does-not-repro` if both types are retained (or
correctly removed only when truly unreferenced, matching an equivalent
control); `changed-behavior` if the shape of the loss differs from what is
described above.
