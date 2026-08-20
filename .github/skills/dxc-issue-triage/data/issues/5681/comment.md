> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5681](https://github.com/microsoft/DirectXShaderCompiler/issues/5681).

Still an invalid program, but no longer reproduces on `main` (89e2f98e2, `1.9.0.5465`):
`InterlockedMax(b.Load<T>(0).value, 1, original)` now compiles to a clean diagnostic instead of
crashing.

```
error: cannot map resource to handle.
repro.hlsl:9:3: error: Atomic operation targets must be groupshared, Node Record or UAV.
  InterlockedMax(b.Load<T>(0).value, 1, original);
  ^
```

A release history search (`v1.4.1907` .. `v1.9.2607`) confirms this was an access violation on
every release from `v1.6.2104` (the first release to support `-T cs_6_6` /
`ResourceDescriptorHeap`) through `v1.8.2502`, then fixed in `v1.8.2505`:

```
Internal compiler error: access violation. Attempted to read from address 0x0000000000000008
```

[Compiler Explorer](https://godbolt.org/z/vfcsj3ThG) corroborates both ends independently:
CE's oldest DXC (`1.6.2112`) still crashes (`SIGSEGV`), current `dxc_trunk` emits the same
clean diagnostic as the local build above.

Suggested labels: no change — `bug`, `crash`, `diagnostic` and `incorrect-code` all still
describe the report accurately.

Suggested action: close as fixed.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
