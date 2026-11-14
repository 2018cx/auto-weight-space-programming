"""Task entrypoint. The harness calls run(...) and records the returned dict in a result manifest."""


def run(model: str, adapter: str | None = None, split: str = "test", limit: int | None = None) -> dict:
    """Evaluate `model` (a Hugging Face id or local path; `adapter` an optional LoRA) on this task.

    Returns {"score": float, "n": int, "per_item": [...]} at minimum. per_item lets anyone recompute the score.
    """
    raise NotImplementedError
