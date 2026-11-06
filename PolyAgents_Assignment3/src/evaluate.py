"""Score a predictions file: exact-match accuracy, group-level bootstrap CI, breakdowns, tokens and cost proxy.

Run:  python src/evaluate.py outputs/baseline_dev_predictions.jsonl --params-billion 8
Writes: outputs/<name>_metrics.json and outputs/<name>_examples.md (selected input/output examples)
"""
import argparse
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from scoring import exact_match, is_correct  # noqa: E402


def group_bootstrap(rows, n_boot=2000, seed=0):
    """95% percentile CI for Acc_EM, resampling whole variation groups (items in a group are not independent)."""
    by_g = defaultdict(list)
    for r in rows:
        by_g[r["group"]].append(r["correct"])
    groups = list(by_g.values())
    rng = random.Random(seed)
    accs = []
    for _ in range(n_boot):
        sample = [rng.choice(groups) for _ in groups]
        flat = [c for g in sample for c in g]
        accs.append(sum(flat) / len(flat))
    accs.sort()
    return [accs[int(0.025 * n_boot)], accs[int(0.975 * n_boot) - 1]]


def summarize(rows, params_b):
    acc = exact_match([r["pred"] for r in rows], [r["gold"] for r in rows])
    sub = lambda f: [r for r in rows if f(r)]  # noqa: E731
    acc_of = lambda rs: (round(sum(r["correct"] for r in rs) / len(rs), 4), len(rs)) if rs else (None, 0)  # noqa
    tok = [r.get("prompt_tokens", 0) + r.get("gen_tokens", 0) for r in rows]
    wall = [r["wall_s"] for r in rows if "wall_s" in r]
    return {
        "n": len(rows),
        "acc_em": round(acc, 4),
        "acc_em_95ci_group_bootstrap": [round(x, 4) for x in group_bootstrap(rows)],
        "n_groups": len({r["group"] for r in rows}),
        "n_parse_failed": sum(r["parse_failed"] for r in rows),
        "n_call_failed": sum(r["call_failed"] for r in rows),
        "acc_heuristic_distractor": acc_of(sub(lambda r: r["heuristic_distractor"])),
        "acc_no_heuristic_distractor": acc_of(sub(lambda r: not r["heuristic_distractor"])),
        "acc_by_type": {t: acc_of(sub(lambda r, t=t: r["type"] == t)) for t in sorted({r["type"] for r in rows})},
        "tokens_per_problem_mean": round(statistics.mean(tok), 1),
        "prompt_tokens_total": sum(r.get("prompt_tokens", 0) for r in rows),
        "gen_tokens_total": sum(r.get("gen_tokens", 0) for r in rows),
        # cost proxy defined in A2: parameters (billions) x tokens processed, summed over all calls
        "cost_proxy_Btok_per_problem": round(params_b * statistics.mean(tok), 1),
        "wall_s_median": round(statistics.median(wall), 2) if wall else None,
        "wall_s_mean_excluding_first": round(statistics.mean(wall[1:]), 2) if len(wall) > 1 else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pred_file")
    ap.add_argument("--params-billion", type=float, default=8.0)
    args = ap.parse_args()
    path = Path(args.pred_file)
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    for r in rows:  # re-score from the stored prediction so the evaluator, not the runner, is authoritative
        r["correct"] = is_correct(r["pred"], r["gold"])
    m = summarize(rows, args.params_billion)
    stem = path.stem.replace("_predictions", "")
    (path.parent / f"{stem}_metrics.json").write_text(json.dumps(m, indent=1), encoding="utf-8")

    wrong = [r for r in rows if not r["correct"]]
    right = [r for r in rows if r["correct"]]
    picks = right[:2] + wrong[:4]
    with open(path.parent / f"{stem}_examples.md", "w", encoding="utf-8") as f:
        f.write(f"# Saved input/output examples ({stem})\n\nReal SVAMP dev items; model output verbatim.\n\n")
        for r in picks:
            f.write(f"## {r['id']} (group {r['group']}, type {r['type']}, heuristic distractor="
                    f"{r['heuristic_distractor']})\n\n**Input:** {r['input']}\n\n**Gold:** {r['gold']}  "
                    f"**Parsed prediction:** {r['pred']}  **Correct:** {r['correct']}\n\n"
                    f"**Model output:**\n\n```\n{r['output'].strip()}\n```\n\n")
    print(json.dumps(m, indent=1))


if __name__ == "__main__":
    main()
