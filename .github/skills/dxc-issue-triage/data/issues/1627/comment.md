> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for [#1627](https://github.com/microsoft/DirectXShaderCompiler/issues/1627).

`-include` is still unsupported on `main` (1.9.0.15422, `eff900d5`), and on every release from
v1.4.1907 through v1.9.2607.

```
$ dxc -T ps_6_0 -E main -include forced.h repro.hlsl
dxc failed : Unknown argument: '-include'
```

There is no equivalent spelling: DXC has `-I` (include search path), `-Vi` (trace include
processing) and `-H` (show include nesting), but no forced-include option.

The demand is not historical — a second, unrelated user re-raised this in July 2025 with the
same motivation: injecting a prelude header into third-party shader sources that cannot be
modified. `-I` does not serve that.

Side-by-side with Clang: https://godbolt.org/z/E1xv7nvPa

Clang already has the capability; it is just not exposed by the dxc-compatible driver, so it
currently needs `-Xclang -include -Xclang forced.h`. In that pane the error is
`fatal error: 'forced.h' file not found` — Compiler Explorer is single-file, so the header does
not exist, but reaching a *file lookup* shows the flag was accepted and acted on. DXC fails
earlier, while parsing arguments. So the ask is a driver-level spelling of behaviour that
already exists upstream.

**Labels:** suggest adding `up-for-grabs` and `usability`; keep `low-hanging-fruit`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
