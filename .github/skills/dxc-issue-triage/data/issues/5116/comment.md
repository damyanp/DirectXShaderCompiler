> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5116](https://github.com/microsoft/DirectXShaderCompiler/issues/5116).

Still reproduces on `main` (built from commit `89e2f98e29c289ae8ad9e00dd310104fea9fd7df`).

Compiling the repro at `-T cs_6_6` succeeds silently, exit 0, while the identical source at
`-T cs_6_5` is correctly rejected:

```
repro.hlsl:68:18: error: local resource not guaranteed to map to unique global resource.
        else t = tex2d.SampleGrad(anisoSampler, uv, uvDdx, uvDdy);
```

That asymmetry is present at v1.6.2104 (2021-04-20, the oldest release shipping SM 6.6) and at
v1.9.2607 (today's newest) — both endpoints of the shipped-SM-6.6 range agree, so the tool's
binary search did not need to probe intervening releases individually — and on today's
`dxc_trunk` on Compiler Explorer: <https://godbolt.org/z/eE8co66vG> (pane 1/2: `-T cs_6_6` on
CE's oldest DXC and on trunk, both clean; pane 3: `-T cs_6_5` on trunk, same diagnostic).
Releases older than v1.6.2104 don't apply — SM 6.6 didn't exist yet.

The two separately-actionable items from @llvm-beanz's comment above are both still open:
(1) per that comment's hypothesis, SM 6.6 should also reject this, because
`DXILCondenseResources` doesn't see through the SM 6.6 resource-handle annotations the way it
does for earlier profiles; (2) full control-flow flattening that would eliminate the underlying
`phi`/`undef` (and make the shader legal either way) is a separate change that this triage does
not newly assess.

Current labels (`dxil`, `correctness`, `incorrect-code`) already match this finding.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
