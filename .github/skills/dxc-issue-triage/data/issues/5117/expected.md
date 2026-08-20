# Expected symptom (written before any tool-recorded probe)

Issue #5117 ("Dumping header dependencies to file prevents error output"): the reporter says
that adding header-dependency dumping to a file (`-MD -MF file.d`) prevents dxc's error log
from being printed to the console. They say they currently have to run dxc twice -- once with
`-MD -MF` to get the dependency file, once without it to see diagnostics -- to get both.

"This reproduces" means: given an HLSL source that dxc diagnoses (rejects) when compiled
*without* `-MD -MF`, compiling that same source *with* `-MD -MF <path>` added produces no
diagnostic on stderr and dxc reports success (exit 0), instead of the diagnosed failure.

No repro shader was attached to the issue -- only the flag combination is named. The repro
here is agent-constructed: an otherwise ordinary pixel shader with a single semantic error
(reference to an undeclared identifier), which dxc unambiguously diagnoses in ordinary
compilation. Repro quality: agent-constructed.

`not-compiler-verifiable` does not apply: this is a compiler CLI/diagnostics behavior,
directly observable through `dxc.exe`'s own stdout/stderr and exit code.
