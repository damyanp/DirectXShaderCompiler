> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#3429](https://github.com/microsoft/DirectXShaderCompiler/issues/3429).

Still reproduces on `main` (dxc 1.9.0.5433, commit `13730886e`, Debug), and on **all 20
bisectable release binaries measured from v1.4.1907 (2019-07) through v1.9.2607
(2026-07)**. The minimised repro from
[the 2024-04-28 comment](https://github.com/microsoft/DirectXShaderCompiler/issues/3429#issuecomment-2081259226)
still produces byte-identical output, on the same two source locations:

```
$ dxc -E main -T cs_6_0 repro.hlsl
error: validation errors

repro.hlsl:9:22: error: TGSM pointers must originate from an unambiguous TGSM global variable.
note: at '%13 = phi float addrspace(3)* [ %8, %7 ], [ %22, %11 ]' in block '#5' of function 'main'.
repro.hlsl:15:20: error: TGSM pointers must originate from an unambiguous TGSM global variable.
note: at '%15 = phi float addrspace(3)* [ %22, %19 ], [ %8, %10 ]' in block '#6' of function 'main'.
Validation failed.
```

Repro, with a `-Vd` pane showing the rejected module:
<https://godbolt.org/z/61Gb43GjM>

**The pointer is not ambiguous.** The same compile with `-Vd` succeeds, and every incoming
value of both phis is a GEP into the *same* global — the shader declares only one groupshared
array:

```llvm
%8  = getelementptr [6 x float], [6 x float] addrspace(3)* @"\01?thingies@@3PAMA", i32 0, i32 %1
%22 = getelementptr [6 x float], [6 x float] addrspace(3)* @"\01?thingies@@3PAMA", i32 0, i32 %17
%13 = phi float addrspace(3)* [ %8, %7 ], [ %22, %11 ]
```

In `lib/DxilValidation/DxilValidation.cpp` (~L3820-3849) the chain walk applies only when the
instruction is itself a GEP or a bitcast; anything else with a TGSM pointer result takes the
`else` branch and is rejected without its operands being examined. A `phi` therefore always
fails, however unambiguous its inputs. `dxv.exe` built from this tree rejects the module too,
so this is the in-tree validator and not only the redistributable `dxil.dll`.

`tools/clang/test/LitDXILValidation/GroupShared/tgsm-chained-gep-ambiguous.ll` shows the
rejection of `phi`/`select` is intentional — but every case it covers merges **two different**
globals, which is genuinely ambiguous. Whether the walk should accept a merge whose operands
all resolve to one global, or whether the optimizer should not form such a merge for TGSM, is
a design decision we are not making here.

Two smaller findings:

- **The `-Od` workaround costs all optimization, not just `-O3`.** On `main`, `-Od` and `-O0`
  compile clean; `-O1`, `-O2` and `-O3` all fail with the same rule. At `-O0` the GEP is simply
  repeated in each block and no `phi float addrspace(3)*` is ever formed — the pointer `phi` is
  created by optimization, from `-O1` upward.
- **v1.4.1907 reports the same rule without the `error:` prefix or source location**, instead
  printing `at 0x… inside block … of function main TGSM pointers must originate…`;
  [#2768](https://github.com/microsoft/DirectXShaderCompiler/issues/2768) preserves the same
  older wording.

`hlsl_clang_trunk` compiles this source without forming a merged groupshared pointer; it keeps
the address computation inside each branch (pane 4, checked against a control under the same
flags). Clang does not run the DXIL validator, so this describes its output, not what the rule
would accept.

Suggested label: add `validation` ("Related to validation or signing") alongside `bug`.

---
<sub>Triaged with AI assistance. Compiler output was produced by running the repro; please
flag anything that looks wrong.</sub>
