"""Score one logit-lens-4way item with an open-weight model (optionally plus a LoRA adapter), inside its container.

Reads /app/item.json (prompt and candidates, no answer), writes /app/answer.txt (A-D) and /app/scores.json.
Each candidate's score is its log-likelihood after the prompt minus its log-likelihood with the number lines hidden,
as in Part 1 of the Auto Weight-Space Programming series.
"""
import argparse
import json
import re

HIDDEN = "(numbers hidden)"


def hide_numbers(prompt):
    return re.sub(r"(?m)^\[\d+\] .*(?:\n\[\d+\] .*)*", HIDDEN, prompt, count=1)


def load(model, adapter):
    import torch
    import transformers as T
    tok = T.AutoTokenizer.from_pretrained(model)
    kw = {"dtype": torch.bfloat16 if torch.cuda.is_available() else torch.float32}
    try:  # Qwen3.5 checkpoints are image-text models; Part 1 adapters only attach to that class
        m = T.AutoModelForImageTextToText.from_pretrained(model, **kw)
    except (ValueError, KeyError):
        m = T.AutoModelForCausalLM.from_pretrained(model, **kw)
    if adapter:
        from peft import PeftModel
        m = PeftModel.from_pretrained(m, adapter)
        if max((float(p.abs().sum()) for n, p in m.named_parameters() if "lora_B" in n), default=0.0) == 0.0:
            raise SystemExit(f"adapter {adapter} did not attach to {model}")
    if torch.cuda.is_available():
        m.cuda()
    return tok, m.eval()


def chat(tok, text):
    msg = [{"role": "user", "content": text}]
    try:
        return tok.apply_chat_template(msg, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    except TypeError:
        return tok.apply_chat_template(msg, tokenize=False, add_generation_prompt=True)


def logp(m, p, t):
    import torch
    ids = torch.tensor([p + t], device=m.device)
    with torch.no_grad():
        lg = m(input_ids=ids, use_cache=False).logits[0, len(p) - 1:-1].float()
    return float(torch.log_softmax(lg, -1).gather(-1, torch.tensor(t, device=m.device)[:, None]).sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter", default="")
    ap.add_argument("--item", default="/app/item.json")
    ap.add_argument("--out", default="/app")
    a = ap.parse_args()
    it = json.load(open(a.item))
    tok, m = load(a.model, a.adapter or None)
    P = tok(chat(tok, it["prompt"]), add_special_tokens=False)["input_ids"]
    Ph = tok(chat(tok, hide_numbers(it["prompt"])), add_special_tokens=False)["input_ids"]
    lp, lh = [], []
    for c in it["candidates"]:
        t = tok(c, add_special_tokens=False)["input_ids"]
        lp.append(logp(m, P, t))
        lh.append(logp(m, Ph, t))
    pmi = [x - y for x, y in zip(lp, lh)]
    pick = max(range(len(pmi)), key=pmi.__getitem__)
    open(f"{a.out}/answer.txt", "w").write("ABCD"[pick] + "\n")
    json.dump({"logp": lp, "logp_hidden": lh, "pmi": pmi, "pick": pick}, open(f"{a.out}/scores.json", "w"))


if __name__ == "__main__":
    main()
