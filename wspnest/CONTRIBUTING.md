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

Everything in WSPNest runs on Harbor. A task recipe is a `generate.py` that writes standard Harbor task directories
(instruction, `task.toml`, container, verifier, reference solution). A benchmark adapter has the same shape: its
`generate.py` fetches the upstream benchmark at a pinned commit and writes one Harbor task per upstream instance, so an
adapter is a for loop over task-level Harbor containers.

The reading task from Part 1 of the Auto Weight-Space Programming series generates two variants of the same items:

- **`variant=agent`**: for any Harbor agent and model, including API models. The agent writes A-D to
  `/app/answer.txt`. Internet is off, so it must read the numbers rather than download the model. This is WSP on
  another model.
- **`variant=scorer`**: for open-weight models reading their own weights (auto-WSP). The WSPNest agent
  `wspnest.agents.logprob:LogprobReader` scores the four lists by log-likelihood inside a GPU container, as in Part 1.

```
python -m wspnest generate logit-lens-4way --out tasks_out --opt variant=agent --opt limit=100
harbor run -p tasks_out -a oracle                                  # the reference solution must pass every task
python -m wspnest run logit-lens-4way --opt variant=agent -- -a claude-code -m anthropic/<model>
python -m wspnest run logit-lens-4way --opt variant=scorer -- --agent-import-path wspnest.agents.logprob:LogprobReader \
    --ak model=Qwen/Qwen3.5-4B --ak adapter=<reader LoRA> -e modal
```

`wspnest run` generates the tasks, runs Harbor, and writes a WSPNest result file from Harbor's rewards.

Things to copy from it:
- the task card's credit and license fields;
- the canary in every generated file;
- the oracle solution;
- the reproduction check against published numbers (see the task card's notes).
