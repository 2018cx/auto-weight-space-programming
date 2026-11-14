"""logit-lens-4way: score a model (optionally with a LoRA adapter) on its own neuron-reading items."""
import json
import re

CONFIG = {"Qwen/Qwen3.5-0.8B": "qwen3.5-0.8b", "Qwen/Qwen3.5-2B": "qwen3.5-2b", "Qwen/Qwen3.5-4B": "qwen3.5-4b",
          "Qwen/Qwen3.5-9B": "qwen3.5-9b", "meta-llama/Llama-3.2-3B-Instruct": "llama-3.2-3b-instruct"}
SPLIT = {"validation": "validation", "test": "test_neuron", "test_hard": "test_neuron_hard", "test_layer": "test_layer"}
DATASET = "atharva-naik-1/awsp-neuron-reading"
HIDDEN = "(numbers hidden)"


def hide_numbers(prompt):
    """The same prompt with its number lines (each starts with "[index]") replaced by one placeholder line."""
    return re.sub(r"(?m)^\[\d+\] .*(?:\n\[\d+\] .*)*", HIDDEN, prompt, count=1)


def load_items(model, split, limit):
    from huggingface_hub import hf_hub_download
    cfg = CONFIG.get(model)
    if cfg is None:
        raise SystemExit(f"logit-lens-4way is defined for {sorted(CONFIG)}; {model} would be a cross-model read")
    path = hf_hub_download(DATASET, f"{cfg}/{SPLIT[split]}.jsonl", repo_type="dataset")
    items = [json.loads(l) for l in open(path)]
    return items[:limit] if limit else items


def load_model(model, adapter):
    import torch
    import transformers as T
    tok = T.AutoTokenizer.from_pretrained(model)
    kw = {"dtype": torch.bfloat16 if torch.cuda.is_available() else torch.float32}
    # Qwen3.5 checkpoints are image-text models; the Part 1 adapters were trained on that class, so load it first
    # (loading them on the text-only class silently drops every LoRA weight).
    try:
        m = T.AutoModelForImageTextToText.from_pretrained(model, **kw)
    except (ValueError, KeyError):
        m = T.AutoModelForCausalLM.from_pretrained(model, **kw)
    if adapter:
        from peft import PeftModel
        m = PeftModel.from_pretrained(m, adapter)
        nz = [float(p.abs().sum()) for n, p in m.named_parameters() if "lora_B" in n]
        if not nz or max(nz) == 0.0:
            raise SystemExit(f"the adapter at {adapter} did not attach to {model} (all LoRA weights are zero)")
    m.eval()
    if torch.cuda.is_available():
        m.cuda()
    return tok, m


def chat(tok, text):
    msg = [{"role": "user", "content": text}]
    try:
        return tok.apply_chat_template(msg, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    except TypeError:
        return tok.apply_chat_template(msg, tokenize=False, add_generation_prompt=True)


def seq_logp(m, prompt_ids, target_ids):
    import torch
    ids = torch.tensor([prompt_ids + target_ids], device=m.device)
    with torch.no_grad():
        logits = m(input_ids=ids, use_cache=False).logits[0, len(prompt_ids) - 1:-1].float()
    lp = torch.log_softmax(logits, -1).gather(-1, torch.tensor(target_ids, device=m.device)[:, None])
    return float(lp.sum())


def run(model, adapter=None, split="test", limit=None):
    items = load_items(model, split, limit)
    tok, m = load_model(model, adapter)
    per = []
    for it in items:
        P = tok(chat(tok, it["prompt"]), add_special_tokens=False)["input_ids"]
        Ph = tok(chat(tok, hide_numbers(it["prompt"])), add_special_tokens=False)["input_ids"]
        lp, lh = [], []
        for c in it["candidates"]:
            t = tok(c, add_special_tokens=False)["input_ids"]
            lp.append(seq_logp(m, P, t))
            lh.append(seq_logp(m, Ph, t))
        pmi = [a - b for a, b in zip(lp, lh)]
        pick = max(range(len(pmi)), key=pmi.__getitem__)
        per.append({"id": it["id"], "answer": it["answer"], "pick": pick, "correct": int(pick == it["answer"]),
                    "logp": lp, "logp_hidden": lh})
    return {"score": sum(p["correct"] for p in per) / max(1, len(per)), "n": len(per), "per_item": per}
