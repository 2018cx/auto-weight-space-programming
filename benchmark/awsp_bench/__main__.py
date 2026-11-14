"""python -m awsp_bench list | validate | run <task> --model M [--adapter A] [--split S] [--limit N]"""
import argparse
import datetime
import importlib.util
import json
import os
import platform
import subprocess
import sys

from . import __version__
from .registry import ROOT, TASKS, all_tasks, load_release, load_task


def cmd_list(a):
    for t in all_tasks():
        c, errs = load_task(t)
        flag = "" if not errs else "  [INVALID]"
        print(f"{c['id']:<28} {c['version']:<8} {c['kind']:<9} {'auto' if c['auto'] else 'other':<6} {c['track']:<9} {c['title']}{flag}")


def cmd_validate(a):
    bad = 0
    for t in all_tasks():
        _, errs = load_task(t)
        for e in errs:
            print(f"{t}: {e}")
        bad += bool(errs)
    for f in sorted(os.listdir(os.path.join(ROOT, "releases"))):
        if f.endswith(".yaml"):
            _, errs = load_release(f[:-5])
            for e in errs:
                print(e)
            bad += bool(errs)
    print("ok" if not bad else f"{bad} problem(s)")
    sys.exit(1 if bad else 0)


def _commit():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


def cmd_run(a):
    card, errs = load_task(a.task)
    if errs:
        sys.exit("\n".join(errs))
    spec = importlib.util.spec_from_file_location(f"task_{a.task}", os.path.join(TASKS, a.task, card["entrypoint"]))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = mod.run(model=a.model, adapter=a.adapter, split=a.split, limit=a.limit)
    manifest = {"task": card["id"], "task_version": card["version"], "harness_version": __version__,
                "harness_commit": _commit(), "model": a.model, "adapter": a.adapter, "split": a.split, "limit": a.limit,
                "metric": card["metric"]["name"], "score": out["score"], "n": out["n"],
                "date": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                "python": platform.python_version()}
    os.makedirs(a.out, exist_ok=True)
    stem = f"{card['id']}__{(a.adapter or a.model).replace('/', '_')}__{a.split}"
    json.dump({**manifest, "per_item": out.get("per_item", [])}, open(os.path.join(a.out, stem + ".json"), "w"), indent=1)
    print(json.dumps(manifest, indent=1))


def main():
    ap = argparse.ArgumentParser(prog="awsp_bench")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(f=cmd_list)
    sub.add_parser("validate").set_defaults(f=cmd_validate)
    r = sub.add_parser("run")
    r.add_argument("task")
    r.add_argument("--model", required=True)
    r.add_argument("--adapter", default=None)
    r.add_argument("--split", default="test")
    r.add_argument("--limit", type=int, default=None)
    r.add_argument("--out", default=os.path.join(ROOT, "results"))
    r.set_defaults(f=cmd_run)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
