# Method notes — #5993

**This checkout is a shallow clone (`git rev-parse --is-shallow-repository` → `true`) — do not
use `git log`/`git blame` on it as a dating or "nothing changed" tool without checking that
first.** `git rev-list --count HEAD` from the ground-truth commit reports only **207** total
commits, the earliest reachable commit is dated 2026-03-11, and
`git log --all --oneline -- tools/clang/tools/libclang/CIndex.cpp` finds a single commit whose
diff for that file is "7636 insertions(+), 0 deletions(-)" — the shallow-clone boundary commit,
which necessarily shows every file's full body as a fresh addition, under a commit message
("Fix Test Breakage on WSL (#8263)") about an unrelated test file. The real upstream DXC
repository has thousands of commits on this file's history going back to 2016 (`origin`/
`upstream` remotes point at `damyanp/DirectXShaderCompiler` and
`microsoft/DirectXShaderCompiler`, but a shallow clone doesn't have that history locally), so
this local graph cannot answer "when did this line last change" or "how many commits touched
this file" — any such question needs the real remote history (`gh api`, a full `git fetch
--unshallow`, or GitHub's own history/blame view), not this checkout's `.git`. I initially
drafted a claim of the form "no commits touched this code since the issue was filed, per `git
log`" and retracted it in `notes.md` once this surfaced — the same shape as the skill's
documented "negative result from a command that errored is not a negative result" trap, one
layer over: here the command *succeeds* and returns a real but structurally meaningless answer
(a history graph that is missing everything before the shallow boundary). Worth a pre-flight
`git rev-parse --is-shallow-repository` check before any issue in this batch cites local `git
log` for dating or attribution.
