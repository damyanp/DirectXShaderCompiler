# #5546 -- `discard` grouped as a "flow-control statement" is misleading

## The ask

Doc-update request, not a compiler bug. The reporter points at the Microsoft Learn "Flow
Control" page and says `discard` is misclassified: it does not perform flow control (does not
jump/skip past subsequent statements) the way `break`/`return`/`if`/etc. do; it only flags the
invocation to have its UAV writes and render-target exports elided later. Filed 2023-08-15,
zero comments, no cross-references (`gh api .../timeline` empty).

## Part 1 -- is the docs symptom still there today?

Fetched both pages live (2026-08-19):

- https://learn.microsoft.com/en-us/windows/win32/direct3dhlsl/dx-graphics-hlsl-flow-control
  (page `updated_at: 2025-03-11`) still opens with "A flow-control statement determines at run
  time which block of HLSL statements to execute next... jump (branch) to an instruction other
  than the one on the next line", and still lists `discard` in the same bullet list as `break`,
  `continue`, `do`, `for`, `if`, `switch`, `while`.
- https://learn.microsoft.com/en-us/windows/win32/direct3dhlsl/dx-graphics-hlsl-discard
  (`updated_at: 2021-06-30`) itself is narrower -- "Do not output the result of the current
  pixel" -- and does not independently claim early-exit behavior. The misleading grouping is
  specifically on the parent "Flow Control" index page.

So the reported text is unchanged and still live nearly 3 years after filing.

## Part 2 -- is the underlying technical claim correct? (compiler-verifiable)

Built two otherwise-identical pixel shaders differing only in what happens inside `if (pos.x <
0) { ... }` (`repro.hlsl` = `discard;`, `control-return.hlsl` = `return float4(0,0,0,0);`),
both followed by `buf[0] = 42;` (`RWStructuredBuffer<uint>`) and a final `return`.

`out-main-debug.txt` (repro.hlsl, `-T ps_6_0 -E main`, final DXIL):

```
br i1 %3, label %4, label %5
; <label>:4
  call void @dx.op.discard(i32 82, i1 true)
  br label %5
; <label>:5                    ; preds = %4, %0
  call void @dx.op.bufferStore.i32(... i32 42 ...)
  call void @dx.op.storeOutput.f32(... 1.0 ...)   ; x4, one per component
  ret void
```

`variant-return-control-main-debug.txt` (control-return.hlsl, same command via `run --shader`):

```
br i1 %3, label %5, label %4
; <label>:4                    ; preds = %0  (only reached when NOT taking the early exit)
  call void @dx.op.bufferStore.i32(... i32 42 ...)
  br label %5
; <label>:5                    ; preds = %4, %0
  %6 = phi float [ 1.0, %4 ], [ 0.0, %0 ]
  call void @dx.op.storeOutput.f32(... %6 ...)   ; x4
  ret void
```

This is the decisive contrast: with `discard`, the block containing the buffer write (label
`%5`) is reached from **both** arms of the branch -- the write and every `SV_Target` component
store execute unconditionally, regardless of whether the discard condition was true. With
`return`, the same write lives in a block (label `%4`) reached from only **one** arm; taking
the early-return path skips it outright, and the output value itself becomes a `phi` that
differs per arm. `discard` compiles to a plain (non-terminating) intrinsic call that falls
through; `return` compiles to an actual predicated skip. This matches the reporter's
description exactly: `discard` does not skip subsequent code at the compiler level (the UAV
write is emitted and DXIL keeps it live); whatever "elision" happens for the discarded
invocation is a later, runtime/hardware effect (post-shader helper-lane masking), not something
visible as a branch here. `-fcgl` (pre-DXIL clang codegen, `variant-fcgl-discard-main-debug.txt`
/ `variant-fcgl-return-main-debug.txt`) shows the identical shape one level earlier: `discard`'s
`if.then` block falls through to `if.end` (which contains the buffer store), while `return`'s
`if.then` branches straight to the function's `return` block, bypassing `if.end` entirely.

`match.json` encodes this structurally (discard op textually followed by the buffer store with
no intervening `br i1`) and scores `repro` on `repro.hlsl`. Its control,
`control-return.hlsl` (no `discard` at all), correctly scores `no-repro` (`--expect no-match`,
satisfied) -- confirming the predicate isn't vacuously true for any shader that happens to
contain a buffer write after an `if`.

No release history/bisection applies: this isn't a regression claim, and `discard`'s
kill-without-branch codegen strategy follows directly from stable, long-standing semantics
(mark for later elision, don't terminate the invocation); there is no fix-boundary to locate.
`bisect` was not run.

## Compiler Explorer

Published `repro.hlsl` on Compiler Explorer's oldest DXC (`dxc_1_6_2112`) and `dxc_trunk`
(`manual-case-godbolt-verify.txt`, link recorded via `verdict.json`/`godbolt.txt`:
https://godbolt.org/z/rnEKhGWcY). Both panes reproduce the identical structural shape seen
locally: `br i1 ..., label %3, label %4` / `%3: call @dx.op.discard ...; br label %4` /
`%4: call @dx.op.bufferStore ...` -- the buffer write sits in the block reached from both
arms. Confirms the finding is not specific to the local `main-debug` build.


## Assessment

The documentation symptom is confirmed live today, and the technical premise behind the
request is confirmed by DXC's own compiled output. This repository does not own the affected
page, though: `original_content_git_url` on both fetched pages points at
`github.com/MicrosoftDocs/win32-pr`, a different repo entirely. A dxc compile can verify the
compiler-behavior premise (done above) but cannot verify or produce an edit to that page --
the actual requested action is out of scope for `microsoft/DirectXShaderCompiler`.

- Repro quality: agent-constructed.
- Status: `not-compiler-verifiable` for the literal ask (the deliverable is an edit to an
  external page this repo does not own); the technical claim the ask rests on is verified true
  by compiler evidence, which is included above and cited in the draft comment.
- `text-stale`: not applicable to *this* repo's docs (`docs/` here does not cover this HLSL
  language reference material at all, so there is nothing in `microsoft/DirectXShaderCompiler`
  itself to flag as stale).
- Suggested action: `needs-human-judgement` -- the correct next step is to move/duplicate the
  request to `MicrosoftDocs/win32-pr` (or whichever repo currently owns
  learn.microsoft.com HLSL reference content), which a maintainer should decide/action, not
  this triage.
