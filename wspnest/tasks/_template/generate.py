"""Task recipe: write Harbor task directories for this task. The harness calls generate(out, **options).

Each generated directory is a standard Harbor task: instruction.md, task.toml, environment/Dockerfile,
tests/test.sh (writes /logs/verifier/reward.txt) and solution/solve.sh (the reference solution, used to check the
verifier with `harbor run -a oracle`). Put the canary GUID from CANARY in every file you generate.

A benchmark adapter has the same shape: generate() fetches the upstream benchmark at a pinned commit and writes one
Harbor task per upstream instance (a for loop over task-level Harbor containers).
"""


def generate(out: str, **options) -> int:
    """Write the task directories under `out`; return how many were written."""
    raise NotImplementedError
