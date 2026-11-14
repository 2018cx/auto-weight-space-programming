"""python -m wspnest list | validate | generate <task> --out DIR [--opt k=v] | run <task> [--opt k=v] -- <harbor run args>"""
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


def _load_generator(card, task_id):
    spec = importlib.util.spec_from_file_location(f"task_{task_id}", os.path.join(TASKS, task_id, card["entrypoint"]))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.generate


def _options(pairs):
    out = {}
    for p in pairs or []:
        k, v = p.split("=", 1)
        out[k] = int(v) if v.isdigit() else v
    return out


def cmd_generate(a):
    card, errs = load_task(a.task)
    if errs:
        sys.exit("\n".join(errs))
    n = _load_generator(card, a.task)(a.out, **_options(a.opt))
    print(f"wrote {n} Harbor tasks to {a.out}")
    return card, n


def cmd_run(a):
    """Generate the Harbor tasks, run them with Harbor, and write a WSPNest result manifest from the rewards."""
    card, n = cmd_generate(a)
    jobs = os.path.abspath(a.jobs_dir)
    before = set(os.listdir(jobs)) if os.path.isdir(jobs) else set()
    cmd = ["harbor", "run", "-p", a.out, "-o", jobs] + a.harbor_args
    print("running:", " ".join(cmd))
    subprocess.run(cmd, check=False)
    new = sorted(set(os.listdir(jobs)) - before) if os.path.isdir(jobs) else []
    rewards = {}
    for job in new:
        for root, _, files in os.walk(os.path.join(jobs, job)):
            if "reward.txt" in files:
                try:
                    rewards[os.path.relpath(root, jobs)] = float(open(os.path.join(root, "reward.txt")).read().strip())
                except ValueError:
                    pass
    score = sum(rewards.values()) / len(rewards) if rewards else None
    manifest = {"task": card["id"], "task_version": card["version"], "harness_version": __version__,
                "harness_commit": _commit(), "options": _options(a.opt), "harbor_args": a.harbor_args,
                "harbor_jobs": new, "n_tasks": n, "n_scored": len(rewards), "metric": card["metric"]["name"],
                "score": score, "date": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    os.makedirs(a.results, exist_ok=True)
    path = os.path.join(a.results, f"{card['id']}__{'_'.join(new) or 'nojob'}.json")
    json.dump({**manifest, "per_trial": rewards}, open(path, "w"), indent=1)
    print(json.dumps(manifest, indent=1))


def main():
    ap = argparse.ArgumentParser(prog="wspnest")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(f=cmd_list)
    sub.add_parser("validate").set_defaults(f=cmd_validate)
    g = sub.add_parser("generate", help="write a task's Harbor task directories")
    g.add_argument("task")
    g.add_argument("--out", required=True)
    g.add_argument("--opt", action="append", help="generator option, e.g. --opt model=Qwen/Qwen3.5-4B --opt variant=agent")
    g.set_defaults(f=cmd_generate)
    r = sub.add_parser("run", help="generate, run with Harbor, and record a result manifest; pass Harbor args after --")
    r.add_argument("task")
    r.add_argument("--out", default=os.path.join(ROOT, ".harbor_tasks"))
    r.add_argument("--opt", action="append")
    r.add_argument("--jobs-dir", default=os.path.join(ROOT, "jobs"))
    r.add_argument("--results", default=os.path.join(ROOT, "results"))
    r.add_argument("harbor_args", nargs=argparse.REMAINDER)
    r.set_defaults(f=cmd_run)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
