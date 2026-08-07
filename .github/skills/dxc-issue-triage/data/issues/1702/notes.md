# Triage — #1702 Array as parameter of function

| | |
| --- | --- |
| Opened | 2018-11-13 |
| Labels | `bug`, `shader-linking` |
| Repro quality | **complete** (full shader supplied in the issue) |
| Status vs `main` | **repros** — with a symptom that has shifted since the report |
| History | **always-repro'd** (v1.4.1907 → v1.9.2607) for the silent-miscompile symptom |
| Confidence | **high** |
| Suggested action | **still-valid-keep-open** |

## What was tested

The pixel shader from the issue, verbatim — a function parameter declared as an unsized
array:

```hlsl
float4 Func(float4 a[]) { return a[0]; }
float4 main() : SV_Target0
{
    float4 a[] = {float4(1,1,1,1), float4(1,1,1,1)};
    return Func(a);
}
```

`dxc -T ps_6_0 -E main repro.hlsl`

FXC rejects this with `error X3072: 'a': array dimensions of function parameters must be
explicit`.

## Result on `main` (eff900d54, Debug)

Exit 0. One warning, and a shader body that does nothing:

```
warning: Declared output SV_Target0 not fully written in shader. [-Winline-asm]

define void @main() {
  ret void
}
```

The call to `Func` is silently dropped and `SV_Target0` is never written. No error is issued.

## The symptom changed — and the issue history is partly misleading

This issue was tracked with **two** predicates, because the reported symptom is not the
current one.

**1. The 2018 crash is not present in any shipping release.**
`tristanlabelle` reported the same day that DXC was asserting in
`SROA_Helper::RewriteBitCast`. Bisecting an internal-failure predicate across all 20
bisectable releases shows **no internal failure in any of them**, including the oldest
(v1.4.1907, 2019-07). v1.4.1907 is the earliest release shipping a usable `dxc.exe`, so it is
not possible to say *when* the assert stopped — only that it is absent from everything
checkable. Anyone re-testing this issue against a release build and looking for the reported
crash will conclude "cannot reproduce" — incorrectly.

**2. The miscompile is unchanged since at least 2019.**
v1.4.1907 also produced `define void @main() { ret void }` for this shader. The only thing
that has changed in seven years is that DXC now *warns* that the output is not fully written;
v1.4.1907 emitted no warning at all and additionally mislabelled the signature as fully
written (`SV_Target 0 xyzw ... float xyzw`). So current DXC is marginally better, but the
core defect is untouched.

`llvm-beanz` confirmed in 2024-05 that it still reproduced (godbolt), which matches.

## Assessment

Still a real bug: DXC accepts code FXC rejects and emits a shader that writes nothing, with
only a "not fully written" warning to hint at it. Wrong code is arguably worse than a crash.

Maintainer position (`llvm-beanz`, 2024-05) is that this cannot be fixed without larger
parameter-passing work, will likely be addressed in Clang, and that the DXC draft PR
(#5249) is unlikely to land. That makes it a candidate for "keep open, but track against
Clang" rather than active DXC work.

**Note for whoever actions this:** the issue title and the crash stack in the comments no
longer describe what DXC does. If it stays open, the description is worth refreshing so the
next person does not chase a crash that stopped happening before 2019.

---

## Shareable repro

<https://godbolt.org/z/Tfe5d4fGW> — FXC, DXC 1.6.2112, DXC trunk and Clang trunk.

**This link publishes `repro-cs.hlsl`, not `repro.hlsl`.** The issue reports a pixel shader
and `repro.hlsl` keeps that exactly, as the local evidence. But Clang's DXIL backend cannot
lower *any* pixel shader writing `SV_Target` — a one-line `float4 main() : SV_Target { return
0; }` fails there identically — so a ps pane would show an unrelated error and prove nothing.
`repro-cs.hlsl` restates the same construct as a compute shader so all three compilers answer
the same question on the same input.

The translation is *stronger* evidence than the original, not a compromise. Three compilers,
three different answers:

| Compiler | Result |
| --- | --- |
| FXC `cs_5_0` | `error X3072: 'a': array dimensions of function parameters must be explicit` |
| DXC 1.6.2112 and trunk | accepts, then emits `float undef` stores; **its own validator rejects the module** — `Assignment of undefined values to UAV` / `Validation failed.` |
| Clang trunk | compiles correctly, stores `float 1.000000e+00` |

Verified locally against `main-debug` (`out-main-debug-cs.txt`, exit `0x80004005`) before
publishing, and every pane above was fetched and checked rather than assumed.

**Control:** giving the parameter an explicit size (`float4 a[2]`) compiles cleanly on all
three and stores the real values. The unsized parameter is the variable under test, not array
passing in general.

This also corrects an earlier reading of this issue. The previous link ran Clang with
`-fsyntax-only` and concluded "Clang accepts it with no diagnostic either, so the gap is
shared". That was true but incomplete: Clang does not merely accept it, it *compiles it
correctly*. DXC is the only one of the three that is wrong either way — whichever answer is
right for the language, reject like FXC or accept like Clang, emitting `undef` is not it. That
finding also removes the case for `check-in-clang`: Clang has already handled it.


