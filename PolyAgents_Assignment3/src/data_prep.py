"""Load SVAMP, build model inputs, group related variations, and save a group-level dev/test split.

Run:  python src/data_prep.py
Writes: data/processed/svamp_prepared.jsonl, data/splits/split_v1.json, outputs/data_inspection.json
"""
import json
import random
import re
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "SVAMP.json"
SEED = 42
JACCARD_THRESHOLD = 0.5   # body-token overlap used to group variations of one seed problem
DEV_TARGET = 100          # minimum number of dev problems (whole groups are added until reached)

NUM_RE = re.compile(r"\d+(?:\.\d+)?")


def numbers_in(text):
    return [float(n) for n in NUM_RE.findall(text.replace(",", ""))]


def build_input(body, question):
    """Join Body and Question into one prompt string.

    358/1000 Bodies have no terminal punctuation (e.g. 'If there is a discount of 25 dollars on each pack'),
    so a plain concatenation would run the condition into the question. We add a period only when one is missing
    and collapse whitespace. Numbers, units, '$ 3' style spacing and casing are left unchanged.
    """
    body = " ".join(body.split())
    question = " ".join(question.split())
    if not body.endswith((".", "?", "!")):
        body += "."
    return f"{body} {question}"


def masked_tokens(text):
    text = NUM_RE.sub("#", text.lower())
    return set(re.sub(r"[.,?!$]", " ", text).split())


def group_variations(records, threshold=JACCARD_THRESHOLD):
    """Union-find over Bodies whose number-masked token Jaccard >= threshold.

    SVAMP has no seed-problem identifier, but its ~1,000 items are variations of 100 ASDiv-A seeds that keep most
    of the Body wording. Grouping approximates the seed so that variations of one seed never straddle dev and test.
    """
    toks = [masked_tokens(r["Body"]) for r in records]
    parent = list(range(len(records)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            a, b = toks[i], toks[j]
            if len(a & b) / len(a | b) >= threshold:
                parent[find(i)] = find(j)
    roots = {}
    return [roots.setdefault(find(i), f"g{len(roots):03d}") for i in range(len(records))]


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    groups = group_variations(raw)

    prepared = []
    for rec, gid in zip(raw, groups):
        text_nums = numbers_in(rec["Body"] + " " + rec["Question"])
        eq_nums = numbers_in(rec["Equation"])
        unused = [n for n in text_nums if n not in eq_nums]
        prepared.append({
            "id": rec["ID"],
            "group": gid,
            # model-visible field
            "input": build_input(rec["Body"], rec["Question"]),
            # evaluation-only fields (never sent to a model)
            "answer": float(rec["Answer"]),
            "equation": rec["Equation"],
            "type": "Common-Division" if rec["Type"] == "Common-Divison" else rec["Type"],
            "n_text_numbers": len(text_nums),
            "n_ops": sum(rec["Equation"].count(o) for o in "+-*/"),
            # provisional heuristic, NOT a validated distractor label (see report Sec. II-C)
            "unused_numbers": unused,
            "heuristic_distractor": bool(unused),
        })

    # group-level split
    rng = random.Random(SEED)
    gids = sorted(set(groups))
    rng.shuffle(gids)
    size = Counter(groups)
    dev_groups, n = [], 0
    for g in gids:
        if n >= DEV_TARGET:
            break
        dev_groups.append(g)
        n += size[g]
    dev_set = set(dev_groups)
    split = {
        "version": "split_v1",
        "seed": SEED,
        "grouping": f"number-masked Body token Jaccard >= {JACCARD_THRESHOLD}, union-find",
        "source": "arkilpatel/SVAMP SVAMP.json @ 78e727689e1c1bebfc4be39c446898e8e10b0518",
        "dev_groups": sorted(dev_groups),
        "dev_ids": [p["id"] for p in prepared if p["group"] in dev_set],
        "test_ids": [p["id"] for p in prepared if p["group"] not in dev_set],
    }
    for p in prepared:
        p["split"] = "dev" if p["group"] in dev_set else "test"

    (ROOT / "data" / "processed").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "splits").mkdir(parents=True, exist_ok=True)
    (ROOT / "outputs").mkdir(exist_ok=True)
    with open(ROOT / "data" / "processed" / "svamp_prepared.jsonl", "w", encoding="utf-8") as f:
        for p in prepared:
            f.write(json.dumps(p) + "\n")
    (ROOT / "data" / "splits" / "split_v1.json").write_text(json.dumps(split, indent=1), encoding="utf-8")

    words = [len(p["input"].split()) for p in prepared]
    gsizes = sorted(size.values())
    inspection = {
        "n_records": len(raw),
        "fields": list(raw[0].keys()),
        "type_counts_raw": dict(Counter(r["Type"] for r in raw)),
        "n_body_missing_terminal_punct": sum(not r["Body"].strip().endswith((".", "?", "!")) for r in raw),
        "n_exact_duplicate_body_question": len(raw) - len({(r["Body"], r["Question"]) for r in raw}),
        "n_non_integer_answers": sum(float(r["Answer"]) != int(float(r["Answer"])) for r in raw),
        "ops_per_equation": dict(Counter(p["n_ops"] for p in prepared)),
        "numbers_in_text": dict(sorted(Counter(p["n_text_numbers"] for p in prepared).items())),
        "n_heuristic_distractor": sum(p["heuristic_distractor"] for p in prepared),
        "input_words": {"min": min(words), "median": statistics.median(words), "max": max(words)},
        "n_groups": len(gids),
        "group_size": {"min": gsizes[0], "median": statistics.median(gsizes), "max": gsizes[-1],
                       "singletons": sum(s == 1 for s in gsizes)},
        "split_counts": {"dev": len(split["dev_ids"]), "test": len(split["test_ids"]),
                         "dev_groups": len(dev_groups), "test_groups": len(gids) - len(dev_groups)},
        "dev_heuristic_distractor": sum(p["heuristic_distractor"] for p in prepared if p["split"] == "dev"),
    }
    (ROOT / "outputs" / "data_inspection.json").write_text(json.dumps(inspection, indent=1), encoding="utf-8")
    print(json.dumps(inspection, indent=1))


if __name__ == "__main__":
    main()
