> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5736](https://github.com/microsoft/DirectXShaderCompiler/issues/5736).

Still reproduces on current `main` (commit `89e2f98e2`):

```
$ dxc -T cs_6_3 -Fo test.bin test.hlsl
$ dxc -link -T cs_6_3 -Fo test2.bin test.bin
Internal compiler error: access violation. Attempted to read from address 0x0000000000000000
```

Identical crash text and address to the original 1.7.2207.3 report. Checked
every stable release from v1.6.2106 (2021-07, when `-link` was introduced)
through v1.9.2607 (2026-07): all of them crash the same way. Releases before
v1.6.2106 don't have `-link` at all (`Unknown argument: '-link'`), so this has
reproduced for as long as the option has existed.

@elasota's root-cause theory above checks out as far as this triage went:
linking the same shader compiled as a **library** target instead (so it uses
`createHandleForLib` and carries the resource global variables `AddGlobals`
expects) does not crash:

```
$ dxc -T lib_6_3 -Fo control-lib.bin control-lib.hlsl
$ dxc -link -T cs_6_3 -Fo control-lib2.bin control-lib.bin
[exit] 0
```

So the crash is specific to feeding a non-library (`createHandle`-based)
module into the linker, consistent with the theory that `DxilLinkJob::AddGlobals`
never learns about that module's resources and a later out-of-bounds lookup
walks off the end of the (for this module, empty) resource list.

No fix appears to have landed for this since the 2024-07-30 comment.

Current labels (`bug`, `crash`, `shader-linking`, `incorrect-code`) already
describe this well; no change suggested.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
