> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#4958](https://github.com/microsoft/DirectXShaderCompiler/issues/4958).

Still reproduces on `main` (Debug build at commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`):

```
$ dxc -T hs_6_6 -E mainHS -Fo output.dxil repro.hlsl
Internal compiler error: LLVM Assert
```

The trapped assert is:

```
assert(Index < Length && "Invalid index!")
llvm::ArrayRef<class llvm::Value *>::operator []
```
called from `StoreVectorOrStructArray`, inside HLSL's SROA pass
(`SROA_Helper::RewriteForStore`) — matching @Keenuts' comment exactly: the pass is rewriting a
store into `gProjTextureMaps` before that global is eliminated as dead. Continuing execution
past the trap (as an `NDEBUG`/Release build would) hits an access violation in the same call
chain, so this is one defect, not two.

Bisecting stable releases: `v1.6.2104` compiles this cleanly; `v1.6.2106` is the first release
that crashes, with the exact stderr and address the original report quotes
(`Internal compiler error: access violation. Attempted to read from address
0xFFFFFFFFFFFFFFFF`). It has reproduced in every release since — including the newest
catalogued stable build, `v1.9.2607` — and on Compiler Explorer's `dxc_trunk`
(`error: cast<X>() argument of incompatible type!`, the same underlying internal-failure class
reported through a different build configuration). [Compiler Explorer
repro](https://godbolt.org/z/zdcvTzcd7) (older DXC + trunk). Confirmed DXIL-only — the identical
shader compiled with `-spirv` succeeds, matching @Keenuts' comment.

One correction to the original report: re-testing `ARRAY_SIZE` today, only `0` (an empty
array) compiles cleanly — `2`, which the report says "appears to succeed", crashes on current
`main` just like `1`, `3` and `5` do. The bug looks slightly broader than originally described,
not narrower.

Existing labels (`bug`, `dxil`, `crash`) already look correct; no changes suggested.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
