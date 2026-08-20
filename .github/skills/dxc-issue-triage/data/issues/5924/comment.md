> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5924](https://github.com/microsoft/DirectXShaderCompiler/issues/5924).

Still reproduces on `main` (commit `89e2f98e2`):

```
repro.hlsl:13:17: error: member reference base type 'float' is not a structure or union
        return t.xx;
               ~^~~
repro.hlsl:19:44: note: in instantiation of member function 'StyleClipper<float>::func' requested here
        return input.color + StyleClipper<float>::func(input.color.x).x;
                                                  ^
```

Confirmed the issue's workaround: declaring `func`'s parameter as literal
`float` instead of `float_t` makes the same `t.xx` compile cleanly. A plain
top-level `float t; return t.xx;` also compiles clean. So this is specific
to a swizzle whose base's *static* type is a template type parameter that
later resolves to a scalar, not to scalar swizzles in general.

Release history: unprobeable before v1.7.2308 (DXC's first release with
template support — earlier releases reject `template` itself), and
reproduces identically on every stable release from v1.7.2308 through
v1.9.2607 and on `main`; it has never worked in any template-capable
release.

@damyanp's comment above ("this _looks_ like it works in clang") checks out
under a controlled comparison: [Compiler Explorer](https://godbolt.org/z/h5q7acrv9)
shows the classic DXC frontend (`dxc_trunk`) failing with the diagnostic
above while the new Clang-based HLSL frontend (`hlsl_clang_trunk`) compiles
this exact source to DXIL, computing `t.xx` as `color.x + color.x`. Since
that comparison the `check-in-clang` label asked for is now answered,
suggest swapping it for `type-system` to track the observed
templated-vs-non-templated scalar member-access inconsistency.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
