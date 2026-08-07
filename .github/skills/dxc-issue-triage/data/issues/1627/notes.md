# Triage — #1627 force include file

| | |
| --- | --- |
| Opened | 2018-10-24 |
| Labels | `enhancement`, `low-hanging-fruit` |
| Repro quality | **agent-constructed** (feature request, no shader in the issue) |
| Status vs `main` | **repros** — feature still absent |
| History | **always-repro'd** (v1.4.1907 → v1.9.2607) |
| Confidence | **high** |
| Suggested action | **enhancement-not-bug** — still wanted, still unimplemented |

## What was tested

A shader referencing a macro defined only in a separate header, compiled with a forced
include:

```hlsl
// repro.hlsl
float4 main() : SV_Target { return FORCED_VALUE; }
```
```c
// forced.h
#define FORCED_VALUE float4(1,2,3,4)
```

`dxc -T ps_6_0 -E main -include forced.h repro.hlsl`

## Result

```
dxc failed : Unknown argument: '-include'
```

Same on every release from v1.4.1907 to v1.9.2607.

I also checked `dxc --help` for any alternative spelling. DXC has `-I` (add include *search
path*), `-Vi` (trace include processing) and `-H` (show include nesting) — but **no
forced-include option at all**. (MSVC-style `/FI` cannot be tested on Compiler Explorer's Linux
builds, where a `/`-prefixed argument is treated as a path; `dxc --help` on Windows lists no
such flag.) So there is no workaround short of editing the shader source.

## Assessment

Still unimplemented after 7 years, and it is labelled `low-hanging-fruit`.

The demand is demonstrably live rather than historical: the issue was re-raised on 2025-07-18
by a second, unrelated user (`rbratta`) with the same motivation as the original reporter —
compiling third-party shader sources that cannot be edited to add an `#include`, where a
prelude header needs to be injected from the build system. That use case is not served by
`-I`.

Clang already has this capability — but note it is **not** reachable as a bare `-include` in
the dxc-compatible driver, which rejects that with `unknown argument '-include'; did you mean
'-Xclang -include'?`. It works today as `-Xclang -include -Xclang forced.h`. So the ask is a
driver-level spelling of behaviour that already exists upstream, not new functionality.

**Suggested handling:** good `up-for-grabs` candidate. Confirm it is still wanted, then expose
`-include` (and probably `/FI`) in the dxc driver.

---

## Shareable repro

Originally recorded as *deliberately none*: the entire observable DXC behaviour is
`dxc failed : Unknown argument: '-include'`, which prose states just as clearly.

**That decision was reversed** once Clang was put beside it — https://godbolt.org/z/E1xv7nvPa

The two panes fail differently, and the difference is the finding. DXC fails while parsing
arguments. Clang, given `-Xclang -include -Xclang forced.h`, gets as far as
`fatal error: 'forced.h' file not found` — CE is single-file, so the header genuinely does not
exist, and *reaching a file lookup at all* is what proves the flag was accepted and acted on.

So the single-file limitation, which looked like a reason not to publish a link, turned out to
supply the evidence.
