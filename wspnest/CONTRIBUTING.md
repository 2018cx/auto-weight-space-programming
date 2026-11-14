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

## Worked example: `tasks/logit-lens-4way`

The reading task from Part 1 of the Auto Weight-Space Programming series shows both ways a task can run.

- **Model-scoring version** (`run.py`): for open-weight models, including auto-WSP, where the model reads its own
  weights. The model is shown 128 weights of one of its own neurons and four candidate token lists. Each list is
  scored by log-likelihood with the numbers minus log-likelihood with the numbers hidden.
  `python -m wspnest run logit-lens-4way --model Qwen/Qwen3.5-4B --adapter <reader>`
- **Harbor version** (`harbor/make_harbor_tasks.py`): for any agent and model Harbor supports, including API models.
  It generates one Harbor task per item (`instruction.md`, `task.toml`, `environment/Dockerfile`, `tests/`,
  `solution/solve.sh`). The agent writes a letter to `/app/answer.txt`, and the verifier checks it. Internet is
  switched off, so the agent has to read the numbers rather than download the model. This version is WSP on another
  model, not auto-WSP.
  ```
  python3 tasks/logit-lens-4way/harbor/make_harbor_tasks.py --model Qwen/Qwen3.5-4B --split validation --limit 100 --out harbor_tasks/
  harbor run -p harbor_tasks/ -a oracle                  # every task must pass with the reference solution
  harbor run -p harbor_tasks/ -a <agent> -m <model>
  ```

Things to copy from it:
- the task card's credit and license fields;
- the canary in every generated file;
- an oracle solution, so the verifier can be checked;
- a reproduction check against published numbers (see the task card's notes).
