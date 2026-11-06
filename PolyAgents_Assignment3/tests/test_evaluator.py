"""Hand-checked evaluator test on CONSTRUCTED outputs (not model outputs).

Run:  python tests/test_evaluator.py
Expected, worked by hand:
  case                                    parsed   gold   correct
  a) '...5 + 4 = 9\nAnswer: 9'            9        9      yes
  b) 'Answer: 9.0'                        9.0      9      yes   (numeric equality, not string)
  c) '8 + 12 + 4 = 24 ... Answer: 21'     21       9      no    (distractor absorbed)
  d) 'The total is **1,414** apples.'     1414     1414   yes   (no Answer line -> last number; comma removed)
  e) 'I cannot determine this.'           None     3      no    (format failure, still counted in N)
  f) '' (failed call)                     None     51     no
  g) 'Answer: 7\n...Answer: 8'            8        7      no    (last Answer line wins)
  => 3 of 7 correct, Acc_EM = 3/7 = 0.428571...
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from scoring import exact_match, parse_answer  # noqa: E402

CASES = [
    ("John has 5 apples and buys 4 more. 5 + 4 = 9\nAnswer: 9", 9, 9.0),
    ("Answer: 9.0", 9, 9.0),
    ("8 + 12 + 4 = 24, then 24 - 3 = 21.\nAnswer: 21", 9, 21.0),
    ("The total is **1,414** apples.", 1414, 1414.0),
    ("I cannot determine this.", 3, None),
    ("", 51, None),
    ("Answer: 7\nWait, recheck.\nAnswer: 8", 7, 8.0),
]


def main():
    preds = []
    for text, gold, expected in CASES:
        p = parse_answer(text)
        assert p == expected, f"parse mismatch for {text!r}: got {p}, expected {expected}"
        preds.append(p)
    acc = exact_match(preds, [g for _, g, _ in CASES])
    assert abs(acc - 3 / 7) < 1e-12, acc
    print(f"parsed = {preds}")
    print(f"Acc_EM computed = {acc:.6f}; expected by hand = 3/7 = {3/7:.6f}  -> PASS")


if __name__ == "__main__":
    main()
