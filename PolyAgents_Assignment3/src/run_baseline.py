"""Monolithic single-pass baseline: one Ollama model, one zero-shot chain-of-thought call per problem.

Run:  python src/run_baseline.py --config config/baseline_checkpoint.json [--limit N]
Output: one JSON line per problem with the raw model text, parsed answer, token counts and latency.
Re-running resumes: ids already in the output file are skipped.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from scoring import is_correct, parse_answer  # noqa: E402


def call_ollama(cfg, prompt):
    payload = {"model": cfg["model"], "stream": False, "options": cfg["options"],
               "messages": [{"role": "user", "content": prompt}]}
    t0 = time.perf_counter()
    r = requests.post(cfg["ollama_url"], json=payload, timeout=cfg["timeout_s"])
    r.raise_for_status()
    d = r.json()
    return {"text": d["message"]["content"],
            "prompt_tokens": d.get("prompt_eval_count", 0),
            "gen_tokens": d.get("eval_count", 0),
            "wall_s": round(time.perf_counter() - t0, 3),
            "load_s": round(d.get("load_duration", 0) / 1e9, 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/baseline_checkpoint.json")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    cfg = json.loads((ROOT / args.config).read_text())
    limit = args.limit or cfg.get("limit")
    template = (ROOT / cfg["prompt_file"]).read_text(encoding="utf-8")

    ids = json.loads((ROOT / cfg["split_file"]).read_text())[f"{cfg['split']}_ids"]
    if cfg["split"] != "dev":
        sys.exit("Refusing to run on the test split at this checkpoint.")
    recs = {}
    for line in open(ROOT / "data" / "processed" / "svamp_prepared.jsonl", encoding="utf-8"):
        r = json.loads(line)
        recs[r["id"]] = r
    ids = ids[:limit] if limit else ids

    out = ROOT / cfg["output"]
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        done = {json.loads(l)["id"] for l in open(out, encoding="utf-8") if l.strip()}

    with open(out, "a", encoding="utf-8") as f:
        for k, pid in enumerate(ids, 1):
            if pid in done:
                continue
            rec = recs[pid]
            prompt = template.format(problem=rec["input"])   # only the model-visible field is used
            res, err, attempts = None, None, 0
            while attempts <= cfg["max_retries"] and res is None:
                attempts += 1
                try:
                    res = call_ollama(cfg, prompt)
                except Exception as e:  # failed call -> scored as incorrect, logged
                    err = repr(e)
            pred = parse_answer(res["text"]) if res else None
            row = {"id": pid, "group": rec["group"], "run": cfg["run_name"], "model": cfg["model"],
                   "input": rec["input"], "gold": rec["answer"], "pred": pred,
                   "correct": is_correct(pred, rec["answer"]), "parse_failed": res is not None and pred is None,
                   "call_failed": res is None, "error": err, "attempts": attempts,
                   "heuristic_distractor": rec["heuristic_distractor"], "type": rec["type"],
                   **({k2: v for k2, v in res.items() if k2 != "text"} if res else {}),
                   "output": res["text"] if res else ""}
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(f"[{k}/{len(ids)}] {pid} gold={rec['answer']} pred={pred} ok={row['correct']} "
                  f"tok={row.get('prompt_tokens', 0)}+{row.get('gen_tokens', 0)} t={row.get('wall_s')}s", flush=True)


if __name__ == "__main__":
    main()
