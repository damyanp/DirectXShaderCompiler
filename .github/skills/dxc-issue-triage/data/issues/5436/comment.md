> [!WARNING]
> **Draft — not a maintainer decision.** AI-assisted triage for
> [#5436](https://github.com/microsoft/DirectXShaderCompiler/issues/5436).

Still unaddressed on `main` (89e2f98e2). Neither function has the requested assert or a
comment justifying its absence:

`ValidateDxilOperationCallInProfile`'s opcode switch (`lib/DxilValidation/DxilValidation.cpp`):

```cpp
  default:
    // TODO: make sure every Opcode is checked.
    // Skip opcodes don't need special check.
    break;
  }
}
```

`ValidateHandleArgs`'s opcode switch (the function that now wraps
`ValidateHandleArgsForInstruction`):

```cpp
  default:
    ValidateHandleArgsForInstruction(CI, Opcode, ValCtx);
    break;
  }
}
```

The second one isn't a no-op — every opcode not in the four excluded cases still gets
`ValidateHandleArgsForInstruction`'s generic handle-argument checks — so it's closer to
the "prove it's safe and comment why" alternative this issue offers. But there's still no
comment recording that reasoning and no assert either, so the ask (an explicit signal
either way) is unmet for both functions.

For context: this is the issue @bob80905 linked from a PR #5982 review thread
(2023-11-08) in reply to a maintainer's "Do we have an issue tracking this?" on the same
switch — so it's a confirmed, still-open gap, not a stale one-off suggestion.

This isn't something a shader repro or a Compiler Explorer link can demonstrate: an
opcode silently skipped by an empty default produces identical `dxc` output whether or
not the assert exists (asserts don't affect codegen), so there's nothing to compile that
would show the gap either way. No CE link is included for that reason.

Labels (`enhancement`, `tech-debt`, `validation`) still look right; no change suggested.

---
<sub>Triaged with AI assistance. This assessment was produced by reading the current
source directly; please flag anything that looks wrong.</sub>
