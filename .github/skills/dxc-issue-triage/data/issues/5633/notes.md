# #5633 -- DXC should warn on statically checkable out-of-bounds

## Summary

`repro.hlsl` is the reporter's exact Compiler Explorer shader (godbolt.org/z/frv3neY5x),
reproduced byte-for-byte (only HTML-entity-escaped `<`/`>` were undone). It declares
`struct LineStyle { float phaseShift; uint _pad[1u]; };` behind a `StructuredBuffer`, and
indexes the one-element `_pad` array with the compile-time literal `2000`:

```hlsl
return float(lineStyles[45]._pad[2000]).xxxx;
```

`lineStyles[45]` indexes the runtime-sized buffer itself, which the reporter correctly
notes cannot be bounds-checked statically -- that is not the ask. `._pad[2000]` indexes a
*fixed-size* (`[1]`) member with a literal index, which is fully knowable at compile time.
The ask is that DXC diagnose this second access.

## Primary result: reproduces, silently, on every probeable release

`dxc -T ps_6_0 -E main -spirv repro.hlsl` (`out-main-debug.txt`) exits 0 with **empty
stderr** and bakes the literal straight into the SPIR-V access chain:
`%23 = OpAccessChain %_ptr_Uniform_uint %lineStyles %int_0 %uint_45 %int_1 %int_2000`,
where `%int_2000 = OpConstant %int 2000` against a one-element `%_arr_uint_uint_1`. The
same is true of plain DXIL codegen (no `-spirv`): the buffer load's constant byte offset
folds the literal `2000` in directly (`i32 8004 = 4 + 2000*4`), again with no diagnostic
(the only warning present there is an unrelated `'binding' attribute ignored`, from
`[[vk::binding]]` being meaningless outside `-spirv`).

`match.json` scores this as `repro` when three things hold together: exit 0 (the compile
actually finished), the literal `2000` reaching the emitted access chain (`int_2000\b` --
proves this specific out-of-bounds constant was actually compiled through, not dropped by
an unrelated early failure), and no `warning`/`error` token anywhere in combined
stdout+stderr. `diag-selftest.hlsl` (`variant-diag-selftest-main-debug.txt`) proves the
absence clause is not vacuous: this build's `-spirv` path is fully capable of printing
`warning:` text (an unrelated implicit-conversion truncation warning), so the primary
probe's silence is not an artefact of this build never emitting diagnostics at all.

`bisect --linear` (mandatory here: `match.json` is an absence-of-diagnostic predicate, so
a monotonic assumption is exactly the trap the skill warns about) reports **every**
probeable stable release, v1.5.2010 (2020-10-22) through v1.9.2607 (2026-07-29), scores
`repro`; only v1.4.1907 is excluded, correctly, as `invalid-probe` (it predates SPIR-V
codegen entirely -- `SPIR-V CodeGen not available`). This is `always-repro'd` across the
full checkable SPIR-V history, well before the reporter's 2023-08-31 filing.

## DXC already has a related check -- it just doesn't reach this shader

`tools/clang/test/SemaHLSL/array-index-out-of-bounds.hlsl` already exercises exactly the
diagnostic the reporter is asking for, `err_hlsl_array_element_index_out_of_bounds`
("array index N is out of bounds"), for a *plain* local array
(`int array[2]; array[2] = 0;`). Re-running that test file against `main-debug` still
passes (`-verify`, exit 0) -- the check is alive on `main`.

Four labelled controls (`control-existing-check-*.hlsl`, scored against the secondary
`match-existing-check.json`, not against the primary repro) isolate exactly why it never
fires for this issue's repro:

| control | shape | fires? |
| --- | --- | --- |
| `control-existing-check-plain.hlsl` | `float arr[1]; return arr[2000];` | **yes** (`repro` under `match-existing-check.json`) |
| `control-existing-check-binop.hlsl` | `float arr[1]; float y = arr[2000] + 0.0; return y.xxxx;` | **yes** |
| `control-existing-check-swizzle.hlsl` | `float arr[1]; return arr[2000].xxxx;` | no |
| `control-existing-check-member.hlsl` | `struct S { float pad[1]; }; return s.pad[2000];` (no swizzle) | no |

Two independent gaps compound in the reporter's shader, and both are cited directly from
`tools/clang/lib/Sema/SemaChecking.cpp` on `main-debug`:

1. **`Sema::CheckArrayAccess(const Expr *expr)`** (the entry point used for a completed
   full expression, e.g. a `return` operand) only unwraps `ParenImpCasts`, the `*`/`&`
   unary operators, `?:`, and an HLSL subscript-operator call before checking whether what
   remains is an `ArraySubscriptExpr`; every other wrapping node falls through to a bare
   `default: return;` (source lines ~8553-8603). A swizzle (`.xxxx`) is exactly such a
   wrapper, so `control-existing-check-swizzle.hlsl` is silently exempted purely because
   of the trailing swizzle -- confirmed by `control-existing-check-binop.hlsl`, which
   shows that wrapping in *some* further expression is not itself sufficient to suppress
   the check (only a swizzle/member-access wrapper is, per this table).
2. **`IsTailPaddedMemberArray`** (source lines ~8371-8399, called from
   `Sema::CheckArrayAccess(BaseExpr, IndexExpr, ...)`) deliberately skips the warning
   whenever the array is exactly size 1 *and* is a struct field (`FieldDecl`), with the
   comment "these are often used to approximate flexible arrays in C89 code" --
   `control-existing-check-member.hlsl`'s `struct S { float pad[1]; }` matches this
   heuristic exactly, independent of any swizzle.

The reporter's `_pad` field is `uint _pad[1]` -- syntactically indistinguishable from the
C89 flexible-array-member idiom this heuristic exists to exempt, even though here it is
declared, and used, as ordinary padding. Combined with the trailing `.xxxx` swizzle, both
suppression paths apply independently to the same shader, guaranteeing total silence for
precisely the pattern in this issue. This reframes the issue: DXC does not lack a
static-bounds diagnostic outright, it has one whose two documented exemptions both happen
to cover the reporter's exact repro.

## Cross-compiler: not fixed in the Clang-based successor either

`godbolt --compilers dxc_1_6_2112,dxc_trunk,hlsl_clang_trunk`
(https://godbolt.org/z/KG9b5j1f8, `manual-case-godbolt-verify.txt`): `dxc_1_6_2112` and
`dxc_trunk` both match the local result exactly (silent, `int_2000` baked into the access
chain). `hlsl_clang_trunk` compiles cleanly too, with only an unrelated
"argument unused ... -Qembed_debug" note; its SPIR-V shows the same literal
(`%22 = OpConstant %18 2000`) reaching an `OpInBoundsAccessChain` with no diagnostic. The
in-progress Clang-based HLSL front end has not (yet) picked up a broader check either.

## Not-compiler-verifiable half

The reporter also asks, as an open question, whether this is "invalid SPIR-V and UB" --
that is a SPIR-V-spec / driver-validation question, not something `dxc`'s own diagnostics
can answer, and this triage does not attempt it. The compiler-verifiable half (should
`dxc` warn/error) is the one addressed above.

## Verdict

- status: `repros` (the reported silence is present, unconditionally, right now)
- repro-quality: `complete`
- history: `always-repro'd` across v1.5.2010..v1.9.2607 (v1.4.1907 invalid-probe: no
  SPIR-V codegen) and on `main-debug`
- suggested-action: `still-valid-keep-open` -- a legitimate, still-open diagnostic gap;
  not a crash, not a regression, and (per the source reading above) closer to "narrow an
  existing check's two exemptions" than "add a diagnostic from scratch"
- labels: `bug`, `enhancement`, `diagnostic` are all still apt. `bug` is, if anything,
  slightly *more* defensible after this triage than before it: the missing diagnostic
  isn't merely an unimplemented feature, it's an existing safety check whose own
  exemptions accidentally cover this exact shape. No removal proposed. `check-in-clang`
  is deliberately not proposed -- that comparison is already done above, and the label's
  own description marks it as a to-do for work not yet performed.
