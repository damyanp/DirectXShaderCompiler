# Why cmd.txt differs from cmd-as-filed.txt

The issue body pastes the arguments as:

    -Zpc -spirv -fspv-target-env=vulkan1.1 _o3 -E -T cs_6_0 -HV 2021

Two transcription artifacts: `_o3` is not a dxc option (`-O3` is), and `-E -T cs_6_0` leaves
`-E` without an entry-point name, so `-T` would be consumed as the entry name and `cs_6_0` as
an input file. The reporter drove `IDxcCompiler3::Compile` with an argument array, so the
literal pasted string is not what ran. `cmd-as-filed.txt` is the de-garbled reconstruction:
`-O3` for `_o3`, and `-E main` restored.

`cmd.txt` — the command every compiler in the history search receives — drops `-spirv`,
`-fspv-target-env`, `-Zpc`, `-O3` and `-HV 2021`, because none of them is load-bearing and
two of them would shorten the measurable history for reasons unrelated to this bug:

- `-spirv`: v1.4.1907 ships no SPIR-V codegen (`SPIR-V CodeGen not available`), so the
  SPIR-V arm cannot probe the oldest release. llvm-beanz's 2023-07-31 comment says the crash
  happens for DXIL as well, and the `variant-as-filed-flags-*` capture measures the full
  SPIR-V flag set on ground truth: identical failure.
- `-HV 2021`: old releases answer `Unknown HLSL version: 2021`, which is an `invalid-probe`.
  The `variant-hv2021-*` capture measures it on ground truth: identical failure.

Both variants are captured rather than assumed. See `notes.md`.
