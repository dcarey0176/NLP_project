# PolyAgents — Assignment 3 checkpoint code

Team PolyAgents (Sirish Gurung, Dennis Carey, Matthew Russo, Justin Comellas), Florida Polytechnic University.
This is `PolyAgents_Assignment3.zip`; the methodology report is submitted separately as `PolyAgents_Assignment3.pdf`.

Heterogeneous multi-agent workflows vs. monolithic LLMs on SVAMP. This ZIP contains the **minimum working
implementation**: data preparation, a group-level dev/test split, a single-model baseline runner, a shared
answer parser/scorer, an evaluator test, and saved outputs from a checkpoint run on the development split.

## What is implemented vs. planned

| Component | Status |
|---|---|
| Load SVAMP, preprocess, inspect (`src/data_prep.py`) | Implemented, run |
| Variation-group split, 103 dev / 897 test (`data/splits/split_v1.json`) | Implemented, run |
| Monolithic zero-shot CoT runner via Ollama (`src/run_baseline.py`) | Implemented, run on dev with a **stand-in model** (Llama-3-8B) |
| Shared parser + exact-match scorer (`src/scoring.py`) | Implemented |
| Evaluator: accuracy, group-bootstrap CI, breakdowns, tokens, cost proxy (`src/evaluate.py`) | Implemented, run |
| Hand-checked evaluator test (`tests/test_evaluator.py`) | Implemented, passes |
| B0 with the planned model Qwen2.5-14B | Planned |
| B1 single-model program-aided control + sandboxed executor | Planned |
| T1 three-agent team (Gemma-2-2B / Llama-3.2-3B / Qwen2.5-Coder-3B) + orchestrator | Planned |
| Optional T2 (same-family team), B2 (majority vote) | Optional |
| Any test-split run | Not done (the runner refuses `split: test` at this checkpoint) |

## Setup

1. Python 3.10+ and `pip install -r requirements.txt` (only `requests` is needed).
2. Install Ollama (https://ollama.com) and pull the checkpoint model: `ollama pull llama3` (Meta-Llama-3-8B-Instruct, Q4_0, ~4.7 GB).
   The planned final baseline is `ollama pull qwen2.5:14b`.
3. Get the data (not redistributed here; MIT License, Patel et al., NAACL 2021):

```bash
mkdir -p data/raw
curl -L -o data/raw/SVAMP.json https://raw.githubusercontent.com/arkilpatel/SVAMP/78e727689e1c1bebfc4be39c446898e8e10b0518/SVAMP.json
```

## Run (from this folder)

```bash
python src/data_prep.py                       # -> data/processed/svamp_prepared.jsonl, data/splits/split_v1.json, outputs/data_inspection.json
python tests/test_evaluator.py                # hand-checked scorer test, prints PASS
python src/run_baseline.py --config config/baseline_checkpoint.json   # dev split, resumable; add --limit 5 for a quick try
python src/evaluate.py outputs/baseline_dev_predictions.jsonl --params-billion 8
```

On a CPU laptop (i7-1355U, 16 GB RAM) the baseline takes ~25 s per problem (~45 min for 103 dev problems).

## Important settings (`config/baseline_checkpoint.json`)

- model `llama3:latest` (stand-in), prompt `prompts/baseline_zero_shot_cot.txt`
- temperature 0, seed 42, `num_predict` 512, `num_ctx` 2048, 1 retry on a failed HTTP call
- split `split_v1` (seed 42, number-masked Body-token Jaccard >= 0.5 grouping)

## Output files (`outputs/`)

- `data_inspection.json` — counts used in Section II of the report
- `baseline_dev_predictions.jsonl` — one row per dev problem: input, gold, raw model output, parsed prediction, correctness, tokens, latency
- `baseline_dev_metrics.json` — accuracy, 95% group-bootstrap CI, breakdowns, token totals, cost proxy
- `baseline_dev_examples.md` — saved input/output examples (correct and incorrect)
- `evaluator_test_output.txt` — output of the hand-checked test
- `baseline_run_log.txt` — console log of the run

## Data fields

`input` is the only field sent to a model. `answer`, `equation`, `type`, `unused_numbers` and
`heuristic_distractor` are evaluation-only. `heuristic_distractor` (some number in the text is not used by the
reference equation) is a **provisional** flag, not a validated label.

## External code and services

Ollama (local model serving) and the open model weights. No external APIs, no API keys. All scripts are team-written
(drafted with Claude Code assistance and checked by running them; see the report's AI statement).
