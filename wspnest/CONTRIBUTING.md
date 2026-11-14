# Contributing a task

1. **Ask the original authors first** if the task is built on someone else's work, and link their reply in the PR.
   Credit them in `credit.authors`; list yourself in `credit.adapted_by`.
2. **Check the license.** If the data or code license does not allow copying, do not copy it: set
   `license.redistributed: false` and have `run.py` download from, or call, the original source.
3. **Copy `tasks/_template/`** to `tasks/<task-id>/` and fill in every field of `task.yaml`.
4. **Implement `run(model, adapter, split, limit)`** in the entrypoint. It must return `score`, `n` and `per_item`,
   so anyone can recompute the score.
5. **Baselines.** Report at least one. Write and localize tasks must report a random-edit baseline: random edits are
   often surprisingly strong.
6. **Reproduction check.** If the task comes from a published result, show in the PR that `run.py` reproduces it
   (or explain the difference).
7. **Include the canary GUID** from `CANARY` in your task card (`canary:` field) and in any data files you add.
8. **Run `python -m wspnest validate`** and add a test in `tests/` if the task has non-trivial parsing.

New tasks start on the `frontier` track. **Versioning:** bump the major version if scores are no longer comparable,
the minor version for new items or splits, and the patch version for fixes that keep scores comparable.
